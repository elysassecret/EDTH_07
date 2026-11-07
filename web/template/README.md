# EDTH_07 local UI template

Standalone React/Vite prototype. Synthetic data only; no backend connection.

## Run

```sh
cd web/template
npx --yes pnpm@10 install --frozen-lockfile
npx --yes pnpm@10 dev
```

Open http://127.0.0.1:5174.

## UI

The application imports the official shadcn/ui components directly from `src/components/ui/`. There is no custom UI wrapper layer and no custom CSS for buttons, cards, tabs, dialogs, or dropdowns.

- Default shadcn neutral black theme, defined in `src/styles.css`.
- Stock component variants and sizes.
- CardHeader / CardTitle / CardDescription / CardContent / CardFooter composition.
- SelectGroup around every set of SelectItems.
- ToggleGroup for SHORE / TRUTH.
- Alert for callouts and command feedback.
- Empty for missing context and evidence.
- Field / FieldGroup / FieldSet for settings.
- Sheet for laptop panels; Dialog for focused reviews.
- Sonner for notifications.

The SVG chart is domain visualization, not a custom UI control library. Its geographic styling is the only bespoke CSS. Operational marker colors remain distinct from the neutral interface.

Fonts and coastline assets are local. Satellite imagery and camera frames are not supplied.

## Scenarios

The **Scenarios** button provides monitoring, route approval, contact review, coverage gap, single-asset stale, feed loss, recovery, exercise, and evaluator views. Ages and observation timestamps are illustrative.

- Approvals require a review step.
- Pending commands cannot be submitted twice.
- Accepted, completed, rejected, and unconfirmed are distinct states.
- Unconfirmed delivery requires a status query before retry.
- Feed loss locks commands; restoration requires reconciliation.
- Acknowledging an alert leaves the condition active.
- A gap closes only after a delivered observation.
- Truth annotations are absent from SHORE.
- A/D and C/S shortcuts work only on the focused decision card, and open review rather than submit.

Below 1280px the side panels open as shadcn Sheets, preserving the chart.

## Check

```sh
npx --yes pnpm@10 build
npx --yes pnpm@10 test
npx --yes pnpm@10 test:e2e
# While the dev server is running:
npx --yes pnpm@10 screenshots
```

Playwright requires Chromium. Screenshots and test reports are ignored by Git. Automated accessibility checks are not operational or WCAG certification.

## Branch and scope

Publishable template branch: `c/shadcn-ui-template`. The original `local/swarm-console-template` branch remains local-only.

All template files are under `web/template/`. The existing application and contract are untouched. The template is independent of the operational backend.

Coastline: © OpenStreetMap contributors, ODbL. Other dependencies retain their upstream licenses.
