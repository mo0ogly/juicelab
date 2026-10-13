// Overlay e2e guard : a TD challenge solved in Juice Shop must reach the
// teacher dashboard as a `challenge_solved` event, whatever page the
// student opened first. Driven by run.sh (one fresh container per scenario).
//
// Usage : node solve-sync.mjs <scenario> <shop_base_url> <events_jsonl>
//   juicelab-first      control : open /#/juicelab, then /#/score-board in the
//                       same tab (the path that already worked before the fix)
//   score-board-direct  open /#/score-board in a fresh browser, never /#/juicelab
//   solved-offline      the runner solved directoryListingChallenge over plain
//                       HTTP before any browser connected ; open /#/ only
//   notification-consumed  same offline solve, but a first page load with
//                       config.json blocked lets Juice Shop core consume (ack)
//                       the notification before any student record exists ;
//                       only the backfill on the next load can deliver it
//
// Env : CHROME_BIN (default /usr/bin/google-chrome), E2E_TIMEOUT_MS (default 20000)

import { readFileSync, existsSync } from 'node:fs'
import puppeteer from 'puppeteer-core'

const SCENARIOS = {
  'juicelab-first': { path: '/#/juicelab', thenHash: '#/score-board', expectKey: 'scoreBoardChallenge' },
  'score-board-direct': { path: '/#/score-board', expectKey: 'scoreBoardChallenge' },
  'solved-offline': { path: '/#/', expectKey: 'directoryListingChallenge' },
  'notification-consumed': {
    path: '/#/',
    expectKey: 'directoryListingChallenge',
    primeWithoutConfig: true,
    expectSource: 'juice-shop-backfill',
  },
}

const [scenarioName, base, eventsPath] = process.argv.slice(2)
const scenario = SCENARIOS[scenarioName]
if (!scenario || !base || !eventsPath) {
  console.error('usage: node solve-sync.mjs <' + Object.keys(SCENARIOS).join('|') + '> <shop_base_url> <events_jsonl>')
  process.exit(2)
}
const timeoutMs = Number(process.env.E2E_TIMEOUT_MS || 20000)

function receivedSolve (key) {
  if (!existsSync(eventsPath)) return null
  return readFileSync(eventsPath, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l))
    .find(ev => ev.event_type === 'challenge_solved' && ev.challenge_key === key) ?? null
}

const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_BIN || '/usr/bin/google-chrome',
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
})
let found = null
try {
  if (scenario.primeWithoutConfig) {
    const prime = await browser.newPage()
    await prime.setRequestInterception(true)
    prime.on('request', req => {
      if (req.url().includes('/assets/juicelab/config.json')) req.abort()
      else req.continue()
    })
    await prime.goto(base + scenario.path, { waitUntil: 'networkidle2', timeout: timeoutMs })
    await new Promise(resolve => setTimeout(resolve, 2000))
    await prime.close()
  }
  const page = await browser.newPage()
  page.on('pageerror', err => console.error('[page error] ' + err.message))
  await page.goto(base + scenario.path, { waitUntil: 'networkidle2', timeout: timeoutMs })
  if (scenario.thenHash) {
    // In-app navigation, same tab, no reload.
    await page.evaluate(hash => { window.location.hash = hash }, scenario.thenHash)
  }
  const deadline = Date.now() + timeoutMs
  while (!(found = receivedSolve(scenario.expectKey)) && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 500))
  }
} finally {
  await browser.close()
}

if (found && scenario.expectSource && found.data?.source !== scenario.expectSource) {
  console.log('FAIL ' + scenarioName + ' : challenge_solved ' + scenario.expectKey +
    ' arrived with source=' + (found.data?.source ?? '-') + ', expected ' + scenario.expectSource)
  process.exit(1)
}
if (found) {
  console.log('PASS ' + scenarioName + ' : challenge_solved ' + scenario.expectKey +
    ' received (cohort=' + found.cohort_id + ', source=' + (found.data?.source ?? '-') + ')')
  process.exit(0)
}
console.log('FAIL ' + scenarioName + ' : no challenge_solved for ' + scenario.expectKey +
  ' within ' + timeoutMs + ' ms')
process.exit(1)
