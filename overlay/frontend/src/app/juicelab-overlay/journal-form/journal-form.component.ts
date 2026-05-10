/*
 * juicelab-overlay - Journal form component
 * Forces metacognition before/after each challenge.
 * SPDX-License-Identifier: MIT
 */

import { CommonModule } from '@angular/common'
import { Component, computed, effect, inject, input, signal, untracked } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { MatButtonModule } from '@angular/material/button'
import { MatCardModule } from '@angular/material/card'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatIconModule } from '@angular/material/icon'
import { MatInputModule } from '@angular/material/input'
import { MatTooltipModule } from '@angular/material/tooltip'
import { toObservable, toSignal } from '@angular/core/rxjs-interop'
import { TranslateModule } from '@ngx-translate/core'
import { catchError, of, switchMap } from 'rxjs'

import { type JournalPack } from '../models/juicelab.types'
import { JuicelabPackService } from '../services/juicelab-pack.service'
import { JuicelabStateService } from '../services/juicelab-state.service'
import { JuicelabSyncService } from '../services/juicelab-sync.service'

const MIN_WORDS = 5

@Component({
  selector: 'juicelab-journal-form',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    TranslateModule,
  ],
  template: `
    <mat-card class="journal-form">
      <mat-card-title>
        <mat-icon>edit_note</mat-icon>
        {{ (phase() === 'before' ? 'JUICELAB_JOURNAL_TITLE_BEFORE' : 'JUICELAB_JOURNAL_TITLE_AFTER') | translate }}
      </mat-card-title>
      <div *ngIf="phase() === 'before' && challengeName()" class="challenge-brief">
        <div class="challenge-head">
          <mat-icon>flag</mat-icon>
          <strong>{{ challengeName() }}</strong>
          <span *ngIf="challengeCategory()" class="cat">{{ challengeCategory() }}</span>
          <span *ngIf="challengeDifficulty()" class="diff">{{ challengeDifficulty() }}/6</span>
        </div>
        <div *ngIf="challengeDescription()" class="challenge-desc" [innerHTML]="challengeDescription()"></div>
      </div>
      <ng-container *ngIf="prompt() as p">
        <mat-card-subtitle>{{ p }}</mat-card-subtitle>
      </ng-container>
      <mat-card-content>
        <mat-form-field appearance="outline" style="width: 100%;">
          <textarea
            matInput
            rows="4"
            [ngModel]="text()"
            (ngModelChange)="text.set($event)"
            [placeholder]="'JUICELAB_JOURNAL_PLACEHOLDER' | translate"
          ></textarea>
        </mat-form-field>
        <div class="meta">
          <span>{{ 'JUICELAB_JOURNAL_WORDS' | translate }} : {{ wordCount() }}</span>
          <span *ngIf="phase() === 'after' && wordCount() < 50" class="warn">
            {{ 'JUICELAB_JOURNAL_WARN50' | translate }}
          </span>
          <span *ngIf="!canSave()" class="hint">
            {{ 'JUICELAB_JOURNAL_MINWORDS' | translate:{ n: MIN_WORDS } }}
          </span>
          <span *ngIf="dirty()" class="dirty">{{ 'JUICELAB_JOURNAL_DIRTY' | translate }}</span>
        </div>
      </mat-card-content>
      <mat-card-actions class="actions">
        <button
          mat-flat-button
          color="primary"
          [disabled]="!canSave() || !dirty()"
          (click)="save()"
        >
          <mat-icon>save</mat-icon>
          {{ 'JUICELAB_JOURNAL_SAVE' | translate }}
        </button>
        <span *ngIf="lastSavedAt() as ts" class="saved-badge">
          <mat-icon>check_circle</mat-icon>
          {{ 'JUICELAB_JOURNAL_SAVED_AT' | translate }} {{ ts }}
        </span>
        <button
          *ngIf="phase() === 'after'"
          mat-stroked-button
          color="accent"
          (click)="downloadProof()"
          [matTooltip]="'JUICELAB_JOURNAL_DOWNLOAD_HINT' | translate"
        >
          <mat-icon>download</mat-icon>
          {{ 'JUICELAB_JOURNAL_DOWNLOAD' | translate }}
        </button>
      </mat-card-actions>

      <div *ngIf="phase() === 'after'" class="flag-row">
        <label class="flag-label" for="flag-input">
          <mat-icon>flag_circle</mat-icon>
          {{ 'JUICELAB_FLAG_LABEL' | translate }}
        </label>
        <div class="flag-input-row">
          <input
            id="flag-input"
            type="text"
            class="flag-input"
            [value]="flagInput()"
            (input)="setFlagInput($any($event.target).value)"
            [disabled]="flagVerified() || flagBusy()"
            autocomplete="off"
            spellcheck="false"
          />
          <button
            mat-stroked-button
            color="primary"
            (click)="verifyFlag()"
            [disabled]="!flagInput() || flagVerified() || flagBusy()"
          >
            <mat-icon>verified</mat-icon>
            {{ (flagBusy() ? 'JUICELAB_FLAG_VERIFYING' : 'JUICELAB_FLAG_VERIFY') | translate }}
          </button>
        </div>
        <div *ngIf="flagStatusKey() as key" class="flag-status" [class.ok]="flagVerified()" [class.ko]="!flagVerified()">
          <mat-icon>{{ flagVerified() ? 'check_circle' : 'error' }}</mat-icon>
          {{ key | translate }}
        </div>
      </div>

      <div *ngIf="error() as err" class="error-msg">{{ err }}</div>
    </mat-card>
  `,
  styles: [`
    .journal-form { max-width: 720px; margin: 16px 0; color: inherit; }
    .challenge-brief {
      margin: 8px 16px 16px;
      padding: 12px 14px;
      border-left: 3px solid #38bdf8;
      background: rgba(56, 189, 248, 0.08);
      border-radius: 4px;
    }
    .challenge-head {
      display: flex; align-items: center; gap: 8px;
      font-size: 14px; margin-bottom: 6px;
    }
    .challenge-head mat-icon { font-size: 18px; width: 18px; height: 18px; color: #38bdf8; }
    .challenge-head .cat { font-size: 11px; opacity: 0.7; padding: 1px 6px; border: 1px solid currentColor; border-radius: 4px; }
    .challenge-head .diff { font-size: 11px; opacity: 0.7; }
    .challenge-desc { font-size: 13px; line-height: 1.5; opacity: 0.9; }
    .challenge-desc :is(code, a) { color: inherit; }
    .meta { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; opacity: 0.7; }
    .warn { color: #fbbf24; opacity: 1; }
    .hint { color: #94a3b8; opacity: 1; }
    .dirty { color: #fbbf24; opacity: 1; font-style: italic; }
    .actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .saved-badge {
      display: inline-flex; align-items: center; gap: 4px;
      font-size: 13px; color: #4ade80; opacity: 0.95;
    }
    .saved-badge mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .error-msg { color: #f87171; padding: 8px 16px; font-size: 13px; }
    .flag-row {
      margin: 12px 16px 6px; padding: 12px;
      border: 1px dashed rgba(192, 132, 252, 0.55);
      border-radius: 6px;
      background: rgba(192, 132, 252, 0.06);
    }
    .flag-label {
      display: flex; align-items: center; gap: 6px;
      font-size: 13px; opacity: 0.85; margin-bottom: 6px;
    }
    .flag-label mat-icon { font-size: 18px; width: 18px; height: 18px; color: #c084fc; }
    .flag-input-row { display: flex; gap: 8px; align-items: center; }
    .flag-input {
      flex: 1; padding: 6px 10px; border-radius: 6px;
      border: 1px solid rgba(127,127,127,0.35);
      background: transparent; color: inherit; font: inherit;
      font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
      font-size: 12px;
    }
    .flag-input:disabled { opacity: 0.55; }
    .flag-status {
      display: flex; align-items: center; gap: 6px;
      font-size: 13px; margin-top: 8px;
    }
    .flag-status mat-icon { font-size: 18px; width: 18px; height: 18px; }
    .flag-status.ok { color: #4ade80; }
    .flag-status.ko { color: #f87171; }
  `],
})
export class JournalFormComponent {
  private readonly packSvc = inject(JuicelabPackService)
  private readonly stateSvc = inject(JuicelabStateService)
  private readonly syncSvc = inject(JuicelabSyncService)

  readonly challengeKey = input.required<string>()
  readonly phase = input.required<'before' | 'after'>()
  readonly challengeName = input<string>('')
  readonly challengeDescription = input<string>('')
  readonly challengeCategory = input<string>('')
  readonly challengeDifficulty = input<number>(0)

  readonly MIN_WORDS = MIN_WORDS

  readonly text = signal('')
  readonly lastSavedAt = signal<string | null>(null)
  readonly error = signal<string | null>(null)
  readonly flagInput = signal('')
  readonly flagVerified = signal(false)
  readonly flagBusy = signal(false)
  readonly flagStatusKey = signal<string | null>(null)
  private readonly lastLoadedText = signal('')

  private readonly journal = toSignal(
    toObservable(this.challengeKey).pipe(
      switchMap(k => this.packSvc.getJournal(k).pipe(catchError(() => of(null)))),
    ),
    { initialValue: null as JournalPack | null },
  )

  readonly language = computed(() => this.stateSvc.state().student.language)

  readonly persistedText = computed(() => {
    const challenge = this.stateSvc.state().challenges[this.challengeKey()]
    if (!challenge) return ''
    return this.phase() === 'before'
      ? challenge.journal.before_solve
      : challenge.journal.after_solve
  })

  readonly prompt = computed(() => {
    const lang = this.language()
    const j = this.journal()
    if (j) {
      if (this.phase() === 'before') {
        return lang === 'fr' ? j.journal_prompts.before_solve_fr : j.journal_prompts.before_solve_en
      }
      return lang === 'fr' ? j.journal_prompts.after_solve_fr : j.journal_prompts.after_solve_en
    }
    if (this.phase() === 'before') {
      return lang === 'fr'
        ? 'Avant de chercher : qu est-ce que ce challenge t evoque ? Quelle hypothese as-tu sur la vulnerabilite ? Decris ton plan de recherche en 2 a 4 phrases.'
        : 'Before you start : what does this challenge bring to mind? What is your hypothesis about the vulnerability? Describe your investigation plan in 2 to 4 sentences.'
    }
    return lang === 'fr'
      ? 'Apres resolution : qu as-tu compris de la vulnerabilite ? Comment l aurais-tu detectee plus vite ? Quelle prevention en production ? Reponds en au moins 50 mots.'
      : 'After solving : what did you understand about the vulnerability? How would you have spotted it faster? What is the production prevention? Answer in at least 50 words.'
  })

  readonly wordCount = computed(() => this.text().trim().split(/\s+/).filter(Boolean).length)
  readonly dirty = computed(() => this.text() !== this.lastLoadedText())

  constructor () {
    // Hydrate textarea from persisted state when, and ONLY when, the
    // challenge key or the phase change. Reading state inside this effect
    // would also trigger it after every save (which itself updates state),
    // wiping the "Saved at" badge and overwriting the user's text. We
    // therefore read state via untracked() so the effect only depends on
    // the two inputs that should drive a re-hydrate.
    effect(() => {
      const key = this.challengeKey()
      const phase = this.phase()
      const persisted = untracked(() => {
        const challenge = this.stateSvc.state().challenges[key]
        if (!challenge) return ''
        return phase === 'before' ? challenge.journal.before_solve : challenge.journal.after_solve
      })
      this.text.set(persisted)
      this.lastLoadedText.set(persisted)
      this.lastSavedAt.set(null)
    })
  }

  canSave(): boolean {
    return this.wordCount() >= MIN_WORDS
  }

  save(): void {
    if (!this.canSave()) return
    const snapshot = this.text()
    this.stateSvc.saveJournal(this.challengeKey(), this.phase(), snapshot)
    this.lastLoadedText.set(snapshot)
    const now = new Date()
    const hh = String(now.getHours()).padStart(2, '0')
    const mm = String(now.getMinutes()).padStart(2, '0')
    const ss = String(now.getSeconds()).padStart(2, '0')
    this.lastSavedAt.set(hh + ':' + mm + ':' + ss)

    const s = this.stateSvc.state()
    this.syncSvc.send({
      student_token: s.student.token,
      cohort_id: s.student.cohort,
      event_type: 'journal_filled',
      challenge_key: this.challengeKey(),
      data: {
        phase: this.phase(),
        word_count: this.wordCount(),
        text: snapshot,
      },
      client_timestamp: now.toISOString(),
    })
  }

  /**
   * Request a tamper-evident lab proof from the dashboard. The dashboard
   * pulls the events for this student+challenge from its own SQLite,
   * generates the markdown body and signs it with HMAC-SHA256
   * (DASHBOARD_PROOF_SECRET). The student cannot tamper with the file
   * without invalidating the signature, which is verified by the teacher
   * with verify_proof.py.
   */
  downloadProof(): void {
    const state = this.stateSvc.state()
    const dashUrl = this.syncSvc.getDashboardUrl()
    if (!dashUrl) {
      this.error.set('Dashboard URL non configuree.')
      return
    }
    if (!state.student.token) {
      this.error.set('Aucun token etudiant — recharge la page.')
      return
    }
    const params = new URLSearchParams({
      student_token: state.student.token,
      student_name: this.extractStudentEmail(),
      cohort: state.student.cohort,
      key: this.challengeKey(),
      name: this.challengeName() || this.challengeKey(),
      category: this.challengeCategory() || '',
      difficulty: String(this.challengeDifficulty() || 0),
      description: this.stripHtml(this.challengeDescription() || ''),
    })
    const url = dashUrl.replace(/\/$/, '') + '/api/proof?' + params.toString()
    this.error.set(null)
    fetch(url, { method: 'GET', credentials: 'omit' })
      .then(async (resp) => {
        if (!resp.ok) {
          const txt = await resp.text().catch(() => '')
          throw new Error('HTTP ' + resp.status + ' : ' + txt.slice(0, 200))
        }
        const blob = await resp.blob()
        const filename = this.extractFilename(resp) ||
          ('juicelab-' + this.challengeKey() + '-' + new Date().toISOString().replace(/[:.]/g, '-') + '.md')
        const objUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = objUrl
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(objUrl)
      })
      .catch((err) => {
        this.error.set('Echec du telechargement de la preuve : ' + (err?.message ?? String(err)))
      })
  }

  private extractFilename(resp: Response): string {
    const dispo = resp.headers.get('Content-Disposition') || ''
    const match = /filename="?([^";]+)"?/i.exec(dispo)
    return match ? match[1].trim() : ''
  }

  /**
   * Read the email from the Juice Shop JWT stored in localStorage. The
   * payload is the second base64url segment of the token. We don't verify
   * the signature here — the dashboard /api/proof signs whatever it
   * receives, and the email is shown alongside the student_token in the
   * proof so the teacher can identify the submission. Returns '' if the
   * token is missing or malformed.
   */
  private extractStudentEmail(): string {
    try {
      const token = localStorage.getItem('token')
      if (!token) return ''
      const parts = token.split('.')
      if (parts.length !== 3) return ''
      const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
      const padded = b64 + '=='.slice(0, (4 - b64.length % 4) % 4)
      const json = JSON.parse(atob(padded))
      const email = json?.data?.email ?? json?.email ?? ''
      return typeof email === 'string' ? email : ''
    } catch {
      return ''
    }
  }

  setFlagInput(v: string): void {
    this.flagInput.set(v)
    if (this.flagStatusKey()) this.flagStatusKey.set(null)
  }

  /**
   * POST /api/verify-flag with the student token + challenge key + flag.
   * Server-side, the dashboard recomputes the HMAC of challenge_key with
   * JUICESHOP_CTF_SECRET (shared with Juice Shop core). On match, a
   * flag_verified event is persisted and the +10 bonus shows up in the
   * proof and in the cohort matrix.
   */
  verifyFlag(): void {
    const flag = this.flagInput().trim()
    if (!flag) return
    const dashUrl = this.syncSvc.getDashboardUrl()
    const state = this.stateSvc.state()
    if (!dashUrl || !state.student.token) {
      this.flagStatusKey.set('JUICELAB_FLAG_DISABLED')
      this.flagVerified.set(false)
      return
    }
    this.flagBusy.set(true)
    this.flagStatusKey.set(null)
    const url = dashUrl.replace(/\/$/, '') + '/api/verify-flag'
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_token: state.student.token,
        cohort_id: state.student.cohort,
        challenge_key: this.challengeKey(),
        challenge_name: this.challengeName(),
        flag,
      }),
    })
      .then(async (resp) => {
        if (resp.status === 503) {
          this.flagStatusKey.set('JUICELAB_FLAG_DISABLED')
          this.flagVerified.set(false)
          return
        }
        if (!resp.ok) {
          this.flagStatusKey.set('JUICELAB_FLAG_ERR_NETWORK')
          this.flagVerified.set(false)
          return
        }
        const j = await resp.json().catch(() => ({ valid: false }))
        if (j?.valid) {
          this.flagVerified.set(true)
          this.flagStatusKey.set('JUICELAB_FLAG_OK')
          // Persist locally so the hidden trophy room can render this
          // capture without re-querying the dashboard.
          this.stateSvc.markFlagCaptured(this.challengeKey())
        } else {
          this.flagVerified.set(false)
          this.flagStatusKey.set('JUICELAB_FLAG_KO')
        }
      })
      .catch(() => {
        this.flagStatusKey.set('JUICELAB_FLAG_ERR_NETWORK')
        this.flagVerified.set(false)
      })
      .finally(() => {
        this.flagBusy.set(false)
      })
  }

  private stripHtml(html: string): string {
    const tmp = document.createElement('div')
    tmp.innerHTML = html
    return (tmp.textContent || tmp.innerText || '').trim()
  }
}
