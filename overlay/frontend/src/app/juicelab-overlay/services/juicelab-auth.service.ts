/*
 * juicelab-overlay - Auth state service
 *
 * Centralises the "is the student logged in to Juice Shop" signal so any
 * component that catches a 401 from the phase B mini-endpoint can flip
 * the panel back to the auth-required banner. Avoids cascades of 401s
 * (and the Juice Shop core toast that follows them) when a JWT is
 * expired or revoked.
 *
 * Detection sources :
 *  - localStorage 'token' (>= 20 chars) : main signal
 *  - 'storage' event       : cross-tab login (token written from another tab)
 *  - 'focus' event         : user comes back from login tab/window
 *  - 'visibilitychange'    : tab regains visibility
 *  - 2 s poll              : same-tab login fallback (driven by panel)
 *
 * SPDX-License-Identifier: MIT
 */

import { Injectable, signal } from '@angular/core'

@Injectable({ providedIn: 'root' })
export class JuicelabAuthService {
  readonly isAuthenticated = signal<boolean>(this.detect())

  constructor () {
    if (typeof window !== 'undefined') {
      window.addEventListener('storage', (ev) => {
        if (!ev.key || ev.key === 'token') this.recheck()
      })
      window.addEventListener('focus', () => this.recheck())
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') this.recheck()
      })
    }
  }

  /** Re-read localStorage and update the signal. */
  recheck(): boolean {
    const next = this.detect()
    if (next !== this.isAuthenticated()) {
      this.isAuthenticated.set(next)
    }
    return next
  }

  /**
   * Called by components when they receive a 401 from a phase B endpoint.
   * Flips the signal to false, which causes the panel to hide the tabs
   * and show the login banner.
   */
  markUnauthenticated(): void {
    if (this.isAuthenticated()) {
      this.isAuthenticated.set(false)
    }
  }

  /**
   * Diagnostic snapshot used by the login banner to show why detection
   * fails (token absent vs. too short). Returns null if no token.
   */
  tokenSnapshot(): { length: number, head: string } | null {
    try {
      const tok = localStorage.getItem('token')
      if (!tok) return null
      const head = tok.length <= 12 ? tok : tok.slice(0, 8) + '...' + tok.slice(-4)
      return { length: tok.length, head }
    } catch {
      return null
    }
  }

  private detect(): boolean {
    try {
      const tok = localStorage.getItem('token')
      return !!(tok && tok.length > 20)
    } catch {
      return false
    }
  }
}
