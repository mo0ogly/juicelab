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
 * The service is mounted ONCE for the whole session, ideally from
 * AppComponent or any always-alive component. It is idempotent : the
 * native `socket.on` is registered only once thanks to the
 * `subscribed` guard.
 *
 * SPDX-License-Identifier: MIT
 */

import { Injectable, inject } from '@angular/core'
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

  private subscribed = false
  private tdKeys: Set<string> = new Set()

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

  private handleChallengeSolved(raw: ChallengeSolvedPayload): void {
    const key = raw?.key ?? raw?.challenge ?? ''
    if (!key) return
    // Only interested in challenges that belong to the TD parcours.
    if (this.tdKeys.size > 0 && !this.tdKeys.has(key)) return

    // Update local state idempotently.
    this.stateSvc.markSolved(key)

    // Forward to the dashboard. The flag is included if the Juice Shop
    // CTF mode is on (config/default.yml ctf.showFlagsInNotifications=true)
    // — otherwise the field will be undefined and the dashboard ignores
    // it.
    const s = this.stateSvc.state()
    if (!s.student.token || !s.student.cohort) return
    this.syncSvc.send({
      student_token: s.student.token,
      cohort_id: s.student.cohort,
      event_type: 'challenge_solved',
      challenge_key: key,
      data: {
        flag: raw?.flag ?? raw?.hash ?? null,
        source: 'juice-shop-socket',
      },
      client_timestamp: new Date().toISOString(),
    })
  }
}
