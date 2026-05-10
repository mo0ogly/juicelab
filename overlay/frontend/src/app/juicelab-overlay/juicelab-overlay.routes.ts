/*
 * juicelab-overlay - Routing module
 * Lazy-loaded route /juicelab that renders the main panel.
 * SPDX-License-Identifier: MIT
 */

import { type Routes } from '@angular/router'

export const JUICELAB_ROUTES: Routes = [
  {
    path: 'juicelab',
    loadComponent: async () => {
      const m = await import('./juicelab-panel/juicelab-panel.component')
      return m.JuicelabPanelComponent
    },
  },
]
