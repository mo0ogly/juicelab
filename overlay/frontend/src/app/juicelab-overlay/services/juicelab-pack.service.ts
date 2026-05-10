/*
 * juicelab-overlay - Pack service
 *
 * Phase B (server-side gating, decision 2026-05-09).
 *
 * Hints, quiz scoring, and walkthroughs are now served by the Juice Shop
 * mini-endpoint (routes/juicelab.ts) which enforces progressive reveal and
 * gates the walkthrough on challenge.solved=true. The previously leaky
 * static YAML files under /assets/juicelab/{hints,quiz,walkthroughs} have
 * been removed.
 *
 * Only selected_challenges.yml stays public (it is the TD outline, not a
 * solution). The journal prompts are still loaded as YAML because they
 * are pedagogical questions, not solutions.
 *
 * SPDX-License-Identifier: MIT
 */

import { HttpClient } from '@angular/common/http'
import { Injectable, inject } from '@angular/core'
import { Observable, map, shareReplay } from 'rxjs'
import yaml from 'js-yaml'

import {
  type BriefingPack,
  type HintLevel,
  type HintResponse,
  type JournalPack,
  type JuicelabConfig,
  type Lang,
  type QuizPackPublic,
  type QuizScoreResponse,
  type SelectedChallenge,
  type WalkthroughResponse,
} from '../models/juicelab.types'

@Injectable({ providedIn: 'root' })
export class JuicelabPackService {
  private readonly http = inject(HttpClient)
  private readonly publicBase = '/assets/juicelab'
  private readonly apiBase = '/api/juicelab'

  private readonly cache = new Map<string, Observable<unknown>>()

  /** Load the runtime config (dashboard URL, cohort id, instance label). */
  getConfig(): Observable<JuicelabConfig> {
    return this.http.get<JuicelabConfig>(`${this.publicBase}/config.json`).pipe(
      shareReplay({ bufferSize: 1, refCount: false }),
    )
  }

  /**
   * Set of challenge keys that belong to the TD parcours. Used by the
   * score-board challenge-card to decide whether to show the JuiceLab
   * coach badge. Cached via shareReplay (one fetch per session).
   */
  getTdKeySet(): Observable<Set<string>> {
    return this.getSelectedChallenges().pipe(
      map(list => new Set(list.map(c => c.key))),
      shareReplay({ bufferSize: 1, refCount: false }),
    )
  }

  /** Load the index of selected challenges for the TD (public asset, no solution). */
  getSelectedChallenges(): Observable<SelectedChallenge[]> {
    return this.cachedYaml<{ selected_challenges?: Record<string, unknown> }>(
      `${this.publicBase}/selected_challenges.yml`,
    ).pipe(
      map(data => {
        const entries = (data.selected_challenges ?? {}) as Record<string, Record<string, unknown>>
        const flat: SelectedChallenge[] = Object.entries(entries).map(([key, e]) => ({
          key,
          name_official: (e.name_official as string) ?? key,
          demi_journee: (e.demi_journee as 1 | 2 | 3) ?? 1,
          position: (e.position as number) ?? 0,
          difficulty: (e.difficulty as number) ?? 0,
          category: (e.category as string) ?? '',
        }))
        flat.sort((a, b) => (a.demi_journee - b.demi_journee) || (a.position - b.position))
        return flat
      }),
    )
  }

  /**
   * Fetch the quiz questions stripped of expected answers. Used by the
   * quiz form to render the questions; the actual scoring goes through
   * scoreQuiz() so keywords stay server-side.
   */
  getQuizQuestions(challengeKey: string): Observable<QuizPackPublic> {
    return this.http.get<QuizPackPublic>(`${this.apiBase}/quiz/questions`, {
      params: { key: challengeKey },
      withCredentials: true,
    })
  }

  /**
   * Reveal one hint level. Server enforces progression: requesting N+1 before
   * consuming N returns 403 with `required: <previous level>`.
   */
  getHint(challengeKey: string, level: HintLevel): Observable<HintResponse> {
    return this.http.get<HintResponse>(`${this.apiBase}/hint`, {
      params: { key: challengeKey, level },
      withCredentials: true,
    })
  }

  /**
   * Submit quiz answers and receive a server-computed score. Expected
   * keywords are kept server-side and never sent to the client.
   */
  scoreQuiz(
    challengeKey: string,
    language: Lang,
    answers: { Q1: string | number | null, Q2: string | number | null, Q3: string | number | null },
  ): Observable<QuizScoreResponse> {
    return this.http.post<QuizScoreResponse>(
      `${this.apiBase}/quiz/score`,
      { challenge_key: challengeKey, language, answers },
      { withCredentials: true },
    )
  }

  /**
   * Fetch the canonical walkthrough markdown. Server returns 403 until the
   * Juice Shop core flags the challenge as solved.
   */
  getWalkthrough(challengeKey: string): Observable<WalkthroughResponse> {
    return this.http.get<WalkthroughResponse>(`${this.apiBase}/walkthrough`, {
      params: { key: challengeKey },
      withCredentials: true,
    })
  }

  /** Load the journal prompts pack (questions only, not solutions). */
  getJournal(challengeKey: string): Observable<JournalPack> {
    return this.cachedYaml<JournalPack>(`${this.publicBase}/journal/${challengeKey}.yaml`)
  }

  /** Load the briefing pack (mission + concepts, no solutions). */
  getBriefing(challengeKey: string): Observable<BriefingPack> {
    return this.cachedYaml<BriefingPack>(`${this.publicBase}/briefing/${challengeKey}.yaml`)
  }

  /**
   * Fetch a YAML file as text and parse it once.
   * Detects the Juice Shop SPA fallback (index.html returned for an
   * unknown asset path) and returns a clean "asset not found" error
   * instead of letting js-yaml choke on the HTML comments.
   */
  private cachedYaml<T>(url: string): Observable<T> {
    if (!this.cache.has(url)) {
      this.cache.set(
        url,
        this.http.get(url, { responseType: 'text' }).pipe(
          map(text => {
            const head = text.trimStart().slice(0, 32).toLowerCase()
            if (head.startsWith('<!--') || head.startsWith('<!doctype') || head.startsWith('<html')) {
              throw new Error(`asset not found at ${url} (SPA fallback returned HTML)`)
            }
            try {
              return yaml.load(text) as T
            } catch (err) {
              throw new Error(`failed to parse YAML at ${url}: ${(err as Error).message}`)
            }
          }),
          shareReplay({ bufferSize: 1, refCount: false }),
        ),
      )
    }
    return this.cache.get(url) as Observable<T>
  }
}
