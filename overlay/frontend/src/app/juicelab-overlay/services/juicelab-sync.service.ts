/*
 * juicelab-overlay - Sync service
 *
 * POSTs pedagogical events to the teacher dashboard cloud.
 *
 * Configured at boot from /assets/juicelab/config.json. Falls back to a
 * LocalStorage queue when offline; flushQueue() drains it when the
 * dashboard becomes reachable again.
 *
 * Sends X-Instance-Label header so the dashboard can tell which Juice
 * Shop container in a docker-compose multi-instance setup emitted an
 * event.
 *
 * SPDX-License-Identifier: MIT
 */

import { HttpClient, HttpHeaders } from '@angular/common/http'
import { Injectable, inject } from '@angular/core'
import { Subject, catchError, of } from 'rxjs'

import { type SyncEvent } from '../models/juicelab.types'

const QUEUE_KEY = 'juicelab_sync_queue_v1'

@Injectable({ providedIn: 'root' })
export class JuicelabSyncService {
  private readonly http = inject(HttpClient)

  private dashboardUrl = ''
  private instanceLabel = ''

  /** Public stream of all events emitted (useful for in-app dashboard mirror). */
  readonly events$ = new Subject<SyncEvent>()

  configure(dashboardUrl: string, instanceLabel = ''): void {
    this.dashboardUrl = dashboardUrl
    this.instanceLabel = instanceLabel
    this.flushQueue()
  }

  /** Returns the configured dashboard base URL (empty string if not configured). */
  getDashboardUrl(): string {
    return this.dashboardUrl
  }

  /** Send an event. Falls back to local queue on network error.
   *  For `hint_revealed` events specifically, we enrich the `data` payload
   *  with the student email extracted from the Juice Shop JWT. The
   *  dashboard uses this email as the bridge identity to look up the
   *  matching CTFd team_id when CTFd push (Mode C) is enabled. The email
   *  lives in `data` (not at the top level) so it survives in
   *  events.data_json and a /api/admin/reconcile-awards run can rebuild
   *  the mapping after a dashboard restart. */
  send(event: SyncEvent): void {
    const enriched = this.enrichForCtfd(event)
    this.events$.next(enriched)
    if (!this.dashboardUrl) {
      this.enqueue(enriched)
      return
    }
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'X-Instance-Label': this.instanceLabel,
    })
    this.http
      .post(`${this.dashboardUrl}/api/sync`, enriched, { headers })
      .pipe(catchError(() => { this.enqueue(enriched); return of(null) }))
      .subscribe()
  }

  private enrichForCtfd(event: SyncEvent): SyncEvent {
    if (event.event_type !== 'hint_revealed') return event
    const email = this.extractStudentEmail()
    if (!email) return event
    return {
      ...event,
      data: { ...event.data, student_email: email },
    }
  }

  /** Read the email from the Juice Shop JWT in localStorage. Mirrors the
   *  helper in journal-form.component.ts — kept duplicated here to keep
   *  the sync service self-contained and free of UI imports. Returns ''
   *  when the token is missing, malformed, or has no email claim. */
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

  /** Try to drain the offline queue. */
  flushQueue(): void {
    const queue = this.loadQueue()
    if (queue.length === 0 || !this.dashboardUrl) return
    queue.forEach(ev => { this.send(ev) })
    this.saveQueue([])
  }

  private enqueue(event: SyncEvent): void {
    const queue = this.loadQueue()
    queue.push(event)
    this.saveQueue(queue.slice(-500))
  }

  private loadQueue(): SyncEvent[] {
    const raw = localStorage.getItem(QUEUE_KEY)
    if (!raw) return []
    try { return JSON.parse(raw) as SyncEvent[] } catch { return [] }
  }

  private saveQueue(queue: SyncEvent[]): void {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
  }
}
