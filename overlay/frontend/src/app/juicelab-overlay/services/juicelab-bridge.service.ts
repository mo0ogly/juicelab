/*
 * juicelab-overlay - Bridge service
 *
 * Listens to the Juice Shop core socket.io stream and forwards relevant
 * events into our pedagogical state + sync pipeline. The only event we
 * currently relay is `challenge solved`, which Juice Shop emits when its
 * own challenge engine flips a challenge to solved=true. For challenges
 * that belong to the TD parcours (selected_challenges.yml), we :
 *   - mark the challenge as solved in our local state (timestamp +
 *     persists in localStorage),
 *   - push a `challenge_solved` SyncEvent to the dashboard,
 *   - capture the Juice Shop CTF flag if shown in the notification (mode
 *     ctf.showFlagsInNotifications=true).
 *
 * The service is mounted ONCE for the whole session through bootstrap(),
 * called from the always-mounted Juice Shop sidenav. It is idempotent : the
 * native `socket.on` is registered only once thanks to the
 * `subscribed` guard.
 *
 * SPDX-License-Identifier: MIT
 */

import { Injectable, inject } from '@angular/core'
import { forkJoin } from 'rxjs'
import { ChallengeService } from '../../Services/challenge.service'
import { SocketIoService } from '../../Services/socket-io.service'
import { JuicelabPackService } from './juicelab-pack.service'
import { JuicelabStateService } from './juicelab-state.service'
import { JuicelabSyncService } from './juicelab-sync.service'

interface ChallengeSolvedPayload {
  key?: string
  name?: string
  challenge?: string
  flag?: string
  hash?: string
}

@Injectable({ providedIn: 'root' })
export class JuicelabBridgeService {
  private readonly io = inject(SocketIoService)
  private readonly stateSvc = inject(JuicelabStateService)
  private readonly syncSvc = inject(JuicelabSyncService)
  private readonly packSvc = inject(JuicelabPackService)
  private readonly challengeSvc = inject(ChallengeService)

  private subscribed = false
  private bootstrapped = false
  private tdKeys: Set<string> = new Set()

  /**
   * Full overlay session bootstrap, idempotent. Called from the always-mounted
   * Juice Shop sidenav (core patch) so it runs at app load whatever the first
   * page is, and from the panel / coach dialog as a fallback. Starts the
   * socket listener, ensures the student record, configures the sync target,
   * then forwards TD challenges already solved server-side that never reached
   * the dashboard : solves made over plain HTTP with no tab open, or whose
   * socket notification Juice Shop core consumed before the student token
   * existed (core acks every notification on receipt, so it is not replayed).
   */
  bootstrap(): void {
    this.start()
    if (this.bootstrapped) return
    this.bootstrapped = true
    this.packSvc.getConfig().subscribe({
      next: (cfg) => {
        this.stateSvc.ensureStudent(cfg.cohort_id, cfg.default_language)
        this.syncSvc.configure(cfg.dashboard_url, cfg.instance_label)
        this.backfillSolved()
      },
      error: () => {
        // Do not fabricate a cohort id : config.json must be the single
        // source of truth. Without it no student record exists and nothing
        // is sent ; the panel surfaces the problem to the student.
        this.bootstrapped = false
      },
    })
  }

  private backfillSolved(): void {
    forkJoin([this.packSvc.getTdKeySet(), this.challengeSvc.find()]).subscribe({
      next: ([tdKeys, challenges]) => {
        const local = this.stateSvc.state().challenges
        for (const c of challenges) {
          if (!c.solved || !tdKeys.has(c.key) || local[c.key]?.solved_at) continue
          this.handleChallengeSolved({ key: c.key }, 'juice-shop-backfill')
        }
      },
      error: () => {
        // Juice Shop API unreachable : live socket events still flow, the
        // next app load retries the backfill.
      },
    })
  }

  /**
   * Wire up the socket listener. Safe to call multiple times — only the
   * first invocation actually subscribes. Should be called once from a
   * top-level component or app initializer.
   */
  start(): void {
    if (this.subscribed) return
    this.subscribed = true

    // Cache the TD key set up-front so the socket callback can filter
    // synchronously without an extra HTTP roundtrip per Juice Shop event.
    this.packSvc.getTdKeySet().subscribe({
      next: (set) => { this.tdKeys = set },
      error: () => { this.tdKeys = new Set() },
    })

    try {
      this.io.socket().on('challenge solved', (raw: ChallengeSolvedPayload) => {
        this.handleChallengeSolved(raw)
      })
    } catch {
      // Socket not initialized yet (rare). Retry once on next tick.
      setTimeout(() => {
        try {
          this.io.socket().on('challenge solved', (raw: ChallengeSolvedPayload) => {
            this.handleChallengeSolved(raw)
          })
        } catch {
          // Give up silently — Juice Shop core probably broken.
        }
      }, 1000)
    }
  }

  private handleChallengeSolved(raw: ChallengeSolvedPayload, source = 'juice-shop-socket'): void {
    const key = raw?.key ?? raw?.challenge ?? ''
    if (!key) return
    // Only interested in challenges that belong to the TD parcours.
    if (this.tdKeys.size > 0 && !this.tdKeys.has(key)) return

    // No student record yet (config.json still loading) : leave the local
    // state untouched so backfillSolved() picks this solve up once the
    // record exists, instead of marking it solved and never sending it.
    const s = this.stateSvc.state()
    if (!s.student.token || !s.student.cohort) return

    // Update local state idempotently.
    this.stateSvc.markSolved(key)

    // Forward to the dashboard. The flag is included if the Juice Shop
    // CTF mode is on (config/default.yml ctf.showFlagsInNotifications=true)
    // — otherwise the field will be undefined and the dashboard ignores
    // it.
    this.syncSvc.send({
      student_token: s.student.token,
      cohort_id: s.student.cohort,
      event_type: 'challenge_solved',
      challenge_key: key,
      data: {
        flag: raw?.flag ?? raw?.hash ?? null,
        source,
      },
      client_timestamp: new Date().toISOString(),
    })
  }
}
