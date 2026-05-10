/*
 * juicelab-overlay - Coach dialog
 *
 * Modal launched from a Juice Shop score-board challenge card. Wraps the
 * three pedagogical panels (graduated hints, journal before/after, quiz)
 * for the selected challenge so the student can stay on /#/score-board
 * instead of navigating to /#/juicelab.
 *
 * SPDX-License-Identifier: MIT
 */

import { CommonModule } from '@angular/common'
import { Component, Inject, computed, inject } from '@angular/core'
import { MatButtonModule } from '@angular/material/button'
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog'
import { MatIconModule } from '@angular/material/icon'
import { MatTabsModule } from '@angular/material/tabs'
import { MatTooltipModule } from '@angular/material/tooltip'
import { TranslateModule, TranslateService } from '@ngx-translate/core'

import { BriefingPanelComponent } from '../briefing-panel/briefing-panel.component'
import { HintsPanelComponent } from '../hints-panel/hints-panel.component'
import { JournalFormComponent } from '../journal-form/journal-form.component'
import { QuizFormComponent } from '../quiz-form/quiz-form.component'
import { JuicelabAuthService } from '../services/juicelab-auth.service'
import { JuicelabBridgeService } from '../services/juicelab-bridge.service'
import { JuicelabPackService } from '../services/juicelab-pack.service'
import { JuicelabStateService } from '../services/juicelab-state.service'
import { JuicelabSyncService } from '../services/juicelab-sync.service'

export interface CoachDialogData {
  challengeKey: string
  challengeName: string
  challengeDescription?: string
  challengeCategory?: string
  challengeDifficulty?: number
}

@Component({
  selector: 'juicelab-coach-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatTabsModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    TranslateModule,
    BriefingPanelComponent,
    HintsPanelComponent,
    JournalFormComponent,
    QuizFormComponent,
  ],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>school</mat-icon>
      <span class="title-text">{{ 'JUICELAB_COACH_TITLE' | translate }} - {{ data.challengeName }}</span>
      <span class="score-badge" [matTooltip]="'JUICELAB_SCORE_FORMULA' | translate">
        <span class="score-total">{{ totalScoreLabel() }}</span>
        <span class="score-detail">
          {{ 'JUICELAB_SCORE_CHALLENGE' | translate }} {{ scoreChallenge() }}
          /
          Quiz {{ quizScoreLabel() }}
        </span>
      </span>
      <span class="lang-hint">{{ langTag() }}</span>
    </h2>
    <mat-dialog-content class="coach-content">
      <div *ngIf="!isAuthenticated()" class="auth-warn">
        <mat-icon>lock_person</mat-icon>
        <span>{{ 'JUICELAB_AUTH_WARN' | translate }}</span>
      </div>

      <mat-tab-group *ngIf="isAuthenticated()" mat-stretch-tabs="false">
        <mat-tab [label]="'JUICELAB_TAB_BRIEFING' | translate">
          <juicelab-briefing-panel
            [challengeKey]="data.challengeKey"
            [challengeName]="data.challengeName"
            [challengeDescription]="data.challengeDescription || ''"
            [challengeCategory]="data.challengeCategory || ''"
            [challengeDifficulty]="data.challengeDifficulty || 0"
          ></juicelab-briefing-panel>
        </mat-tab>
        <mat-tab [label]="'JUICELAB_TAB_HINTS' | translate">
          <juicelab-hints-panel [challengeKey]="data.challengeKey"></juicelab-hints-panel>
        </mat-tab>
        <mat-tab [label]="'JUICELAB_TAB_AFTER' | translate">
          <juicelab-journal-form
            [challengeKey]="data.challengeKey"
            [challengeName]="data.challengeName"
            [challengeDescription]="data.challengeDescription || ''"
            [challengeCategory]="data.challengeCategory || ''"
            [challengeDifficulty]="data.challengeDifficulty || 0"
            phase="after"
          ></juicelab-journal-form>
        </mat-tab>
        <mat-tab [label]="'JUICELAB_TAB_QUIZ' | translate">
          <juicelab-quiz-form [challengeKey]="data.challengeKey"></juicelab-quiz-form>
        </mat-tab>
      </mat-tab-group>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-stroked-button (click)="dialogRef.close()">{{ 'JUICELAB_CLOSE' | translate }}</button>
    </mat-dialog-actions>
  `,
  styles: [`
    h2[mat-dialog-title] { display: flex; align-items: center; gap: 10px; margin: 0 0 8px; flex-wrap: wrap; }
    .title-text { flex: 1; min-width: 200px; }
    .lang-hint {
      font-size: 11px; opacity: 0.55; padding: 2px 8px;
      border: 1px solid currentColor; border-radius: 6px;
    }
    .score-badge {
      display: inline-flex; flex-direction: column; align-items: center;
      padding: 4px 12px; gap: 2px;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.45);
      border-radius: 8px;
      cursor: help;
    }
    .score-total {
      font-size: 18px; font-weight: 800; color: #38bdf8; line-height: 1;
    }
    .score-detail { font-size: 10px; opacity: 0.7; line-height: 1.2; }
    .coach-content { min-width: min(820px, 90vw); padding-top: 4px; }
    .auth-warn {
      display: flex; align-items: center; gap: 12px;
      padding: 14px 16px; border-radius: 8px;
      background: rgba(251, 191, 36, 0.12);
      border: 1px solid rgba(251, 191, 36, 0.45);
      font-size: 14px; line-height: 1.45;
    }
    .auth-warn mat-icon { color: #fbbf24; }
  `],
})
export class JuicelabCoachDialogComponent {
  private readonly authSvc = inject(JuicelabAuthService)
  private readonly stateSvc = inject(JuicelabStateService)
  private readonly syncSvc = inject(JuicelabSyncService)
  private readonly packSvc = inject(JuicelabPackService)
  private readonly bridgeSvc = inject(JuicelabBridgeService)
  private readonly translate = inject(TranslateService)
  readonly isAuthenticated = this.authSvc.isAuthenticated

  constructor (
    public readonly dialogRef: MatDialogRef<JuicelabCoachDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public readonly data: CoachDialogData,
  ) {
    // Bootstrap that normally happens in juicelab-panel.ngOnInit. When the
    // student opens the coach from /#/score-board the panel is never
    // mounted, so we replicate the init here : load runtime config, ensure
    // the student record exists, and configure the sync service so the
    // download-proof button can reach the dashboard.
    this.bootstrap()

    // Mirror the Juice Shop active language onto our state so the YAML
    // packs (hints, journal prompts, quiz options) pick the right *_fr /
    // *_en field. Anything other than 'en' falls back to 'fr'.
    this.syncLang()
    this.translate.onLangChange.subscribe(() => this.syncLang())
  }

  private bootstrap(): void {
    // Idempotent — only the first call wires the socket listener for
    // 'challenge solved' events emitted by Juice Shop core.
    this.bridgeSvc.start()
    this.packSvc.getConfig().subscribe({
      next: (cfg) => {
        this.stateSvc.ensureStudent(cfg.cohort_id, cfg.default_language)
        this.syncSvc.configure(cfg.dashboard_url, cfg.instance_label)
      },
      error: () => {
        // Config asset unreachable. We do NOT fabricate a cohort id : that
        // would silently bind the student to a phantom cohort the teacher
        // does not know about. Leave the state empty ; the journal save +
        // download-proof flows will surface a clean error and the user can
        // reload after fixing config.json.
      },
    })
  }

  private syncLang(): void {
    const cur = (this.translate.currentLang ?? this.translate.getDefaultLang() ?? 'en').toLowerCase()
    this.stateSvc.setLanguage(cur.startsWith('en') ? 'en' : 'fr')
  }

  langTag(): string {
    return this.stateSvc.state().student.language === 'en' ? 'EN' : 'FR'
  }

  private readonly challenge = computed(() => this.stateSvc.state().challenges[this.data.challengeKey])

  scoreChallenge(): number {
    return this.challenge()?.score_net ?? 100
  }

  private quizScore(): number | null {
    const q = this.challenge()?.quiz
    if (!q) return null
    if (typeof q.score !== 'number' || q.score === 0) {
      // 0 might mean "not submitted yet" in our state model. We treat
      // strictly: only display the quiz score once the user has actually
      // submitted (which sets a non-zero or explicitly 0 score after submit).
      // Distinguish via lastScore semantics — for now use word_count of
      // answers : if Q1/Q3 are non-empty OR Q2 is set, we assume submitted.
      const answered = (typeof q.Q1 === 'string' && q.Q1.length > 0)
        || q.Q2 !== null
        || (typeof q.Q3 === 'string' && q.Q3.length > 0)
      return answered ? q.score : null
    }
    return q.score
  }

  quizScoreLabel(): string {
    const s = this.quizScore()
    if (s === null) return this.translate.instant('JUICELAB_SCORE_QUIZ_PENDING')
    return String(s)
  }

  totalScoreLabel(): string {
    const ch = this.scoreChallenge()
    const qz = this.quizScore()
    if (qz === null) return ch + '/100*'
    return Math.round((ch + qz) / 2) + '/100'
  }
}
