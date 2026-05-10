/*
 * juicelab-overlay - Quiz form component
 *
 * Phase B: questions are fetched stripped of expected answers via
 * /api/juicelab/quiz/questions. Submission goes to /api/juicelab/quiz/score
 * which holds the keyword answer key server-side and returns only the
 * computed score.
 *
 * SPDX-License-Identifier: MIT
 */

import { CommonModule } from '@angular/common'
import { Component, computed, inject, input, signal } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MatButtonModule } from '@angular/material/button'
import { MatCardModule } from '@angular/material/card'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatIconModule } from '@angular/material/icon'
import { MatInputModule } from '@angular/material/input'
import { MatRadioModule } from '@angular/material/radio'
import { toObservable, toSignal } from '@angular/core/rxjs-interop'
import { TranslateModule, TranslateService } from '@ngx-translate/core'
import { catchError, of, switchMap } from 'rxjs'

import { type QuizPackPublic, type QuizScoreResponse } from '../models/juicelab.types'
import { JuicelabAuthService } from '../services/juicelab-auth.service'
import { JuicelabPackService } from '../services/juicelab-pack.service'
import { JuicelabStateService } from '../services/juicelab-state.service'
import { JuicelabSyncService } from '../services/juicelab-sync.service'

@Component({
  selector: 'juicelab-quiz-form',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatRadioModule,
    TranslateModule,
  ],
  template: `
    <mat-card class="quiz-form">
      <mat-card-title>
        <mat-icon>quiz</mat-icon>
        {{ 'JUICELAB_QUIZ_TITLE' | translate }}
      </mat-card-title>
      <mat-card-subtitle>
        {{ 'JUICELAB_QUIZ_SUBTITLE' | translate }}
      </mat-card-subtitle>
      <mat-card-content *ngIf="quiz() as q; else noQuiz">
        <div *ngFor="let key of questionKeys; let qIdx = index" class="question-block">
          <div class="q-text">{{ key }}. {{ questionText(q.quiz[key]) }}</div>

          <ng-container *ngIf="q.quiz[key].type === 'multiple_choice'; else freeText">
            <mat-radio-group [ngModel]="answerFor(key)" (ngModelChange)="setAnswer(key, $event)" class="options">
              <mat-radio-button
                *ngFor="let opt of optionsFor(q.quiz[key]); let i = index"
                [value]="i"
              >
                {{ opt }}
              </mat-radio-button>
            </mat-radio-group>
          </ng-container>

          <ng-template #freeText>
            <mat-form-field appearance="outline" style="width: 100%;">
              <textarea
                matInput
                rows="3"
                [ngModel]="answerFor(key)"
                (ngModelChange)="setAnswer(key, $event)"
              ></textarea>
            </mat-form-field>
          </ng-template>
        </div>

        <div *ngIf="lastScore() !== null" class="result">
          {{ 'JUICELAB_QUIZ_SCORE' | translate }} : <strong>{{ lastScore() }}</strong> / 100
          <span class="by-q" *ngIf="byQ() as bq">
            (Q1 : {{ bq.Q1 }} - Q2 : {{ bq.Q2 }} - Q3 : {{ bq.Q3 }})
          </span>
        </div>
      </mat-card-content>
      <ng-template #noQuiz>
        <mat-card-content>
          <div class="placeholder">
            {{ 'JUICELAB_QUIZ_NOTAVAILABLE' | translate }}
          </div>
        </mat-card-content>
      </ng-template>
      <mat-card-actions *ngIf="quiz() as q">
        <button mat-flat-button color="primary" [disabled]="!canSubmit() || submitting()" (click)="submit()">
          {{ (submitting() ? 'JUICELAB_QUIZ_SENDING' : 'JUICELAB_QUIZ_SUBMIT') | translate }}
        </button>
      </mat-card-actions>
      <div *ngIf="error() as err" class="error">{{ err }}</div>
    </mat-card>
  `,
  styles: [`
    .quiz-form { max-width: 720px; margin: 16px 0; color: inherit; }
    .question-block { margin-bottom: 20px; }
    .q-text { font-weight: 600; margin-bottom: 8px; }
    .options { display: flex; flex-direction: column; gap: 6px; }
    .result { padding: 12px; background: rgba(76, 175, 80, 0.18); border-radius: 4px; }
    .by-q { font-size: 12px; opacity: 0.65; margin-left: 8px; }
    .placeholder { opacity: 0.55; font-style: italic; padding: 12px; }
    .error { color: #f87171; padding: 8px 16px; font-size: 13px; }
  `],
})
export class QuizFormComponent {
  private readonly packSvc = inject(JuicelabPackService)
  private readonly stateSvc = inject(JuicelabStateService)
  private readonly syncSvc = inject(JuicelabSyncService)
  private readonly authSvc = inject(JuicelabAuthService)
  private readonly translate = inject(TranslateService)

  readonly challengeKey = input.required<string>()

  readonly questionKeys: Array<'Q1' | 'Q2' | 'Q3'> = ['Q1', 'Q2', 'Q3']
  answerQ1: string | number | null = ''
  answerQ2: string | number | null = null
  answerQ3: string | number | null = ''
  readonly lastScore = signal<number | null>(null)
  readonly byQ = signal<QuizScoreResponse['by_question'] | null>(null)
  readonly submitting = signal(false)
  readonly error = signal<string | null>(null)

  readonly quiz = toSignal(
    toObservable(this.challengeKey).pipe(
      switchMap(k => this.packSvc.getQuizQuestions(k).pipe(
        catchError((err) => {
          if (err?.status === 401) this.authSvc.markUnauthenticated()
          return of(null)
        }),
      )),
    ),
    { initialValue: null as QuizPackPublic | null },
  )

  readonly language = computed(() => this.stateSvc.state().student.language)

  questionText(q: { question_fr?: string, question_en?: string }): string {
    return (this.language() === 'fr' ? q.question_fr : q.question_en) ?? ''
  }

  optionsFor(q: { options_fr?: string[], options_en?: string[] }): string[] {
    return (this.language() === 'fr' ? q.options_fr : q.options_en) ?? []
  }

  answerFor(key: 'Q1' | 'Q2' | 'Q3'): string | number | null {
    if (key === 'Q1') return this.answerQ1
    if (key === 'Q2') return this.answerQ2
    return this.answerQ3
  }

  setAnswer(key: 'Q1' | 'Q2' | 'Q3', value: string | number | null): void {
    if (key === 'Q1') this.answerQ1 = value
    else if (key === 'Q2') this.answerQ2 = value
    else this.answerQ3 = value
  }

  private hasAnswer(value: string | number | null): boolean {
    if (value === null || value === undefined) return false
    if (typeof value === 'string') return value.trim().length > 0
    return true
  }

  canSubmit(): boolean {
    return this.hasAnswer(this.answerQ1) && this.hasAnswer(this.answerQ2) && this.hasAnswer(this.answerQ3)
  }

  submit(): void {
    if (!this.canSubmit() || this.submitting()) return
    this.error.set(null)
    this.submitting.set(true)

    const q1Out = this.answerQ1
    const q2Out = typeof this.answerQ2 === 'number' ? this.answerQ2 : null
    const q3Out = this.answerQ3

    this.packSvc.scoreQuiz(this.challengeKey(), this.language(), {
      Q1: q1Out,
      Q2: q2Out,
      Q3: q3Out,
    }).subscribe({
      next: (resp) => {
        this.submitting.set(false)
        this.lastScore.set(resp.score)
        this.byQ.set(resp.by_question)

        this.stateSvc.saveQuiz(
          this.challengeKey(),
          { Q1: String(q1Out), Q2: q2Out, Q3: String(q3Out) },
          resp.score,
        )
        const s = this.stateSvc.state()
        this.syncSvc.send({
          student_token: s.student.token,
          cohort_id: s.student.cohort,
          event_type: 'quiz_completed',
          challenge_key: this.challengeKey(),
          data: {
            score: resp.score,
            q1_score: resp.by_question.Q1,
            q2_score: resp.by_question.Q2,
            q3_score: resp.by_question.Q3,
            answers: { Q1: q1Out, Q2: q2Out, Q3: q3Out },
          },
          client_timestamp: new Date().toISOString(),
        })
      },
      error: (err) => {
        this.submitting.set(false)
        // Erreur consommee localement, pas rethrow (sinon Juice Shop core
        // declenche son toast "An unexpected error occurred undefined").
        if (err?.status === 401) {
          this.authSvc.markUnauthenticated()
          this.error.set(this.translate.instant('JUICELAB_QUIZ_ERR_AUTH'))
        } else if (err?.status === 404) {
          this.error.set(this.translate.instant('JUICELAB_QUIZ_ERR_NOTFOUND'))
        } else {
          this.error.set(this.translate.instant('JUICELAB_QUIZ_ERR_NETWORK', { status: err?.status ?? '?' }))
        }
      },
    })
  }
}
