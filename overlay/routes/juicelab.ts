/*
 * juicelab - Phase B mini-endpoint
 *
 * Server-side gating for the JuiceLab pedagogical overlay. Replaces the
 * previously leaky /assets/juicelab/{hints,quiz,walkthroughs} static files
 * with three authenticated routes that:
 *   - reveal one hint at a time, refusing level N+1 if N has not been
 *     consumed by the same student;
 *   - score quiz answers using keywords kept server-side (the client never
 *     receives the answer key);
 *   - serve walkthroughs only after the Juice Shop core has flagged the
 *     challenge as solved.
 *
 * State is held in-memory per (studentToken, challengeKey). Sufficient for
 * a single-instance TD; for multi-instance or persistent setups, replace
 * with Redis or a Sequelize-backed table.
 *
 * SPDX-License-Identifier: MIT
 */

import fs from 'node:fs/promises'
import path from 'node:path'
import { type Request, type Response } from 'express'
import yaml from 'js-yaml'

import * as security from '../lib/insecurity'
import * as utils from '../lib/utils'
import { challenges } from '../data/datacache'
import { type ChallengeKey } from '../models/challenge'

const PRIVATE_ROOT = path.resolve(process.cwd(), 'data', 'juicelab-private')
const HINT_LEVELS = ['N1', 'N2', 'N3', 'N4', 'N5'] as const
type HintLevel = typeof HINT_LEVELS[number]

interface HintEntry {
  cost_pct: number
  text_fr: string
  text_en: string
  pedagogical_intent: string
}

interface HintsPack {
  challenge_key: string
  schema_version: string
  hints: Record<HintLevel, HintEntry>
}

interface QuizQuestion {
  type: 'free_text' | 'multiple_choice'
  question_fr?: string
  question_en?: string
  expected_keywords_fr?: string[]
  expected_keywords_en?: string[]
  options_fr?: string[]
  options_en?: string[]
  correct?: number
}

interface QuizPack {
  challenge_key: string
  quiz: { Q1: QuizQuestion, Q2: QuizQuestion, Q3: QuizQuestion }
}

const consumedHintsByStudent = new Map<string, Map<string, Set<HintLevel>>>()

function safeKey (raw: unknown): string {
  return String(raw ?? '').replace(/[^a-zA-Z]/g, '').slice(0, 80)
}

function authenticatedStudentToken (req: Request): string | null {
  const token = req.cookies?.token ?? utils.jwtFrom(req)
  if (!token || !security.verify(token)) return null
  const user = security.authenticatedUsers.get(token)
  const email = user?.data?.email
  return email ? String(email) : null
}

function getOrInitConsumed (studentToken: string, challengeKey: string): Set<HintLevel> {
  let perStudent = consumedHintsByStudent.get(studentToken)
  if (!perStudent) {
    perStudent = new Map()
    consumedHintsByStudent.set(studentToken, perStudent)
  }
  let perChallenge = perStudent.get(challengeKey)
  if (!perChallenge) {
    perChallenge = new Set()
    perStudent.set(challengeKey, perChallenge)
  }
  return perChallenge
}

async function loadYaml<T> (filePath: string): Promise<T | null> {
  try {
    const text = await fs.readFile(filePath, 'utf8')
    return yaml.load(text) as T
  } catch {
    return null
  }
}

export function getHint () {
  return async (req: Request, res: Response) => {
    const studentToken = authenticatedStudentToken(req)
    if (!studentToken) return res.sendStatus(401)

    const key = safeKey(req.query.key)
    const level = String(req.query.level ?? '') as HintLevel
    if (!key) return res.status(400).json({ error: 'missing key' })
    if (!HINT_LEVELS.includes(level)) return res.status(400).json({ error: 'invalid level' })

    const consumed = getOrInitConsumed(studentToken, key)
    const idx = HINT_LEVELS.indexOf(level)
    if (idx > 0 && !consumed.has(HINT_LEVELS[idx - 1])) {
      return res.status(403).json({
        error: 'previous hint not consumed',
        required: HINT_LEVELS[idx - 1]
      })
    }

    const pack = await loadYaml<HintsPack>(path.join(PRIVATE_ROOT, 'hints', `${key}.yaml`))
    if (!pack?.hints) return res.status(404).json({ error: 'hints pack not found' })
    const hint = pack.hints[level]
    if (!hint) return res.status(404).json({ error: 'level not found in pack' })

    consumed.add(level)

    return res.json({
      challenge_key: key,
      level,
      cost_pct: hint.cost_pct,
      text_fr: hint.text_fr,
      text_en: hint.text_en,
      consumed_levels: HINT_LEVELS.filter(l => consumed.has(l))
    })
  }
}

export function getQuizQuestions () {
  return async (req: Request, res: Response) => {
    const studentToken = authenticatedStudentToken(req)
    if (!studentToken) return res.sendStatus(401)

    const key = safeKey(req.query.key)
    if (!key) return res.status(400).json({ error: 'missing key' })

    const pack = await loadYaml<QuizPack>(path.join(PRIVATE_ROOT, 'quiz', `${key}.yaml`))
    if (!pack?.quiz) return res.status(404).json({ error: 'quiz pack not found' })

    const stripQ = (q: QuizQuestion) => ({
      type: q.type,
      question_fr: q.question_fr,
      question_en: q.question_en,
      options_fr: q.options_fr,
      options_en: q.options_en,
    })

    return res.json({
      challenge_key: key,
      quiz: {
        Q1: stripQ(pack.quiz.Q1),
        Q2: stripQ(pack.quiz.Q2),
        Q3: stripQ(pack.quiz.Q3),
      },
    })
  }
}

export function scoreQuiz () {
  return async (req: Request, res: Response) => {
    const studentToken = authenticatedStudentToken(req)
    if (!studentToken) return res.sendStatus(401)

    const body = req.body ?? {}
    const key = safeKey(body.challenge_key)
    if (!key) return res.status(400).json({ error: 'missing challenge_key' })
    const lang = body.language === 'en' ? 'en' : 'fr'
    const answers = body.answers ?? {}

    const pack = await loadYaml<QuizPack>(path.join(PRIVATE_ROOT, 'quiz', `${key}.yaml`))
    if (!pack?.quiz) return res.status(404).json({ error: 'quiz pack not found' })

    const scoreOne = (q: QuizQuestion, ans: unknown): number => {
      if (q.type === 'multiple_choice') {
        return ans === q.correct ? 100 : 0
      }
      const keywords = lang === 'fr' ? q.expected_keywords_fr : q.expected_keywords_en
      if (!Array.isArray(keywords) || keywords.length === 0 || typeof ans !== 'string' || !ans) {
        return 0
      }
      const haystack = ans.toLowerCase()
      const hits = keywords.filter(kw => haystack.includes(String(kw).toLowerCase())).length
      return Math.min(100, Math.round((hits / keywords.length) * 100))
    }

    const Q1 = scoreOne(pack.quiz.Q1, answers.Q1)
    const Q2 = scoreOne(pack.quiz.Q2, answers.Q2)
    const Q3 = scoreOne(pack.quiz.Q3, answers.Q3)

    return res.json({
      score: Math.round((Q1 + Q2 + Q3) / 3),
      by_question: { Q1, Q2, Q3 }
    })
  }
}

export function getWalkthrough () {
  return async (req: Request, res: Response) => {
    const studentToken = authenticatedStudentToken(req)
    if (!studentToken) return res.sendStatus(401)

    const key = safeKey(req.query.key)
    if (!key) return res.status(400).json({ error: 'missing key' })

    const challenge = challenges[key as ChallengeKey]
    if (!challenge?.solved) {
      return res.status(403).json({ error: 'challenge not solved yet' })
    }

    let markdown: string
    try {
      markdown = await fs.readFile(path.join(PRIVATE_ROOT, 'walkthroughs', `${key}.md`), 'utf8')
    } catch {
      return res.status(404).json({ error: 'walkthrough not found' })
    }

    return res.json({
      challenge_key: key,
      language: 'fr',
      markdown
    })
  }
}

export function blockPrivateAssets () {
  return (_req: Request, res: Response) => res.sendStatus(404)
}

/**
 * Aggregated read-only view of the in-memory pedagogy state. Intended for
 * the teacher to inspect cohort progress while no full dashboard is in
 * place. Authenticated via a shared secret stored in env var
 * TEACHER_ADMIN_TOKEN. Disabled if the env var is empty or absent.
 */
export function getAdminState () {
  return (req: Request, res: Response) => {
    const expected = process.env.TEACHER_ADMIN_TOKEN
    if (!expected || expected.length < 16) {
      return res.status(503).json({ error: 'admin endpoint disabled (TEACHER_ADMIN_TOKEN not set or too short)' })
    }
    const provided = (req.headers['x-admin-token'] ?? '') as string
    if (provided !== expected) {
      return res.status(401).json({ error: 'invalid admin token' })
    }

    const studentsArr: Array<{
      student_email: string
      challenges: Array<{ challenge_key: string, consumed_levels: HintLevel[] }>
    }> = []
    for (const [email, perChallenge] of consumedHintsByStudent) {
      const challengesArr: Array<{ challenge_key: string, consumed_levels: HintLevel[] }> = []
      for (const [key, set] of perChallenge) {
        challengesArr.push({
          challenge_key: key,
          consumed_levels: HINT_LEVELS.filter(l => set.has(l))
        })
      }
      challengesArr.sort((a, b) => a.challenge_key.localeCompare(b.challenge_key))
      studentsArr.push({ student_email: email, challenges: challengesArr })
    }
    studentsArr.sort((a, b) => a.student_email.localeCompare(b.student_email))

    const solvedArr: Array<{ challenge_key: string, solved: boolean }> = []
    for (const challenge of Object.values(challenges)) {
      if (!challenge?.key) continue
      solvedArr.push({
        challenge_key: String(challenge.key),
        solved: Boolean(challenge.solved)
      })
    }
    solvedArr.sort((a, b) => a.challenge_key.localeCompare(b.challenge_key))

    return res.json({
      generated_at: new Date().toISOString(),
      students_count: studentsArr.length,
      students: studentsArr,
      challenges_solved_global: solvedArr
    })
  }
}
