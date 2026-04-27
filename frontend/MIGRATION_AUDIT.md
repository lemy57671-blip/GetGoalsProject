# PHAN 1 - Tom tat kien truc hien tai

- Repo frontend thuc te nam trong `test/frontend/` va hien dang la mot Next.js App Router app su dung TypeScript, TSX, Tailwind CSS v4, shadcn/ui, Radix UI, `next-themes`, va mot so component tu xay.
- Entry hien tai xoay quanh `app/`:
  - `app/layout.tsx` la root layout.
  - `app/page.tsx` la landing page.
  - `app/(auth)/*` la auth pages.
  - `app/(dashboard)/*` la dashboard pages + dashboard layout.
  - `app/onboarding/page.tsx` va `app/pricing/page.tsx` la hai route ngoai dashboard.
- Phan Next.js-specific hien tai:
  - `next/link` o gan het cac page UI.
  - `usePathname` tu `next/navigation` trong `app/(dashboard)/layout.tsx`.
  - `next/font/google` va metadata/viewport trong `app/layout.tsx`.
  - `Metadata` trong `app/pricing/layout.tsx`.
  - `next-env.d.ts`, `next.config.mjs`, scripts `next dev/build/start`, plugin `next` trong `tsconfig.json`.
- Phan UI thuan co the tai su dung rat cao:
  - `components/ui/*` gan nhu doc lap voi Next.js.
  - `components/audio-player-bar.tsx`.
  - `hooks/*`, `lib/utils.ts`.
  - `public/*`.
  - design tokens va Tailwind CSS trong `app/globals.css`.
- Phan mock/demo/client-only logic dang nam o frontend:
  - `app/page.tsx`: feature/testimonial/faq/stats hard-code.
  - `app/onboarding/page.tsx`: step config, target score, deadline, weak skill options hard-code.
  - `app/(auth)/*`: fake submit bang `setTimeout`, redirect bang `window.location.href`.
  - `app/(dashboard)/dashboard/page.tsx`: `sampleQuestions`.
  - `app/(dashboard)/practice/*`: `TOEIC_PARTS`, `sampleQuestions`, `practiceResults`, `reviewQuestions`.
  - `app/(dashboard)/mock-test/*`: `partOptions`, `skillOptions`, `recentTests`, `mockQuestions`.
  - `app/(dashboard)/progress/page.tsx`: `scoreHistory`, `skillProgress`, `partProgress`, `weeklyActivity`, `heatmap`.
  - `app/(dashboard)/review/page.tsx`: `reviewQuestions`, `notebookItems`, `initialAiMessages`.
  - `app/(dashboard)/settings/page.tsx`: toan bo profile/preferences/subscription state dang hard-code.
  - `components/upgrade-pro-modal.tsx`: fake payment flow bang countdown + simulated confirmation.
- Ket luan nhanh:
  - Co nen migrate sang React + FastAPI: Co.
  - Ly do:
    - UI layer hien tai khong qua phu thuoc SSR hay server actions, nen rat hop de tach khoi Next.
    - Shared UI da co tinh reusable cao, giam duoc chi phi rewrite.
    - Domain data hien tai dang mock o frontend, rat hop de dua sang FastAPI theo domain.
    - Migrate song song giup giu UI/UX gan nhu nguyen ven trong khi dua architecture ve dung production shape.

# PHAN 2 - Phan tich theo tung folder/file

## `app/`

- Vai tro hien tai: chua routing, layouts va page UI theo App Router convention.
- Muc do phu thuoc Next.js: cao.
- Kha nang tai su dung: vua.
- Hanh dong de xuat: refactor vua.
- Ly do:
  - Layout/page convention la cua Next.
  - Nhung phan JSX ben trong tung page phan lon van co the tai su dung.
- Cach migrate cu the:
  - Khong sua truc tiep ngay.
  - Port tung file `page.tsx` sang `src/pages/...`.
  - Port `layout.tsx` sang `src/layouts/...`.
  - Sau khi route React on dinh moi retire dan `app/`.

## `app/layout.tsx`

- Vai tro hien tai: root HTML shell, metadata, viewport, font, analytics.
- Muc do phu thuoc Next.js: cao.
- Kha nang tai su dung: thap cho phan layout wrapper, vua cho design choices.
- Hanh dong de xuat: thay hoan toan.
- Ly do:
  - `Metadata`, `Viewport`, `next/font/google`, `@vercel/analytics/next` la Next-only.
- Cach migrate cu the:
  - `metadata` -> `document.title`, meta tags trong `index.html` hoac route meta manager.
  - `next/font/google` -> import font qua CSS.
  - `Analytics` -> doi sang SDK/doc lap neu can.
  - body class va CSS tokens giu nguyen.

## `app/globals.css`

- Vai tro hien tai: design tokens, Tailwind theme mapping, base styles.
- Muc do phu thuoc Next.js: thap.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: giu nguyen.
- Ly do: day la lop tai san quan trong nhat de preserve UI/UX.
- Cach migrate cu the:
  - Tiep tuc import file nay tu Vite app.
  - Bo sung font variables qua CSS thay vi `next/font`.

## `app/page.tsx`

- Vai tro hien tai: landing page marketing.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: sua nhe.
- Ly do:
  - Chu yeu la JSX + local state + `next/link`.
  - Du lieu marketing dang hard-code, co the tach sang module data.
- Cach migrate cu the:
  - `next/link` -> `Link` cua `react-router-dom`.
  - Dua arrays `features`, `testimonials`, `stats`, `faqs` sang `src/data/marketing.ts`.
  - Port sang `src/pages/marketing/LandingPage.tsx`.

## `app/(auth)/`

- Vai tro hien tai: login, register, forgot-password.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: sua nhe.
- Ly do:
  - UI forms da dung tot.
  - Phu thuoc chinh la `next/link` va `window.location.href`.
  - Logic API hien tai la fake.
- Cach migrate cu the:
  - Port sang `src/pages/auth/*`.
  - `window.location.href` -> `useNavigate`.
  - `setTimeout` fake -> `authService`.
  - Giu `.tsx` de bao toan typing form state va validation.

## `app/(auth)/layout.tsx`

- Vai tro hien tai: wrapper auth.
- Muc do phu thuoc Next.js: cao ve convention, thap ve code.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: sua nhe.
- Ly do: layout rat mo, de chuyen sang `AuthLayout`.
- Cach migrate cu the:
  - Tao `src/layouts/AuthLayout.tsx`.
  - Dat auth routes vao nested route group.

## `app/onboarding/page.tsx`

- Vai tro hien tai: onboarding wizard 5 buoc.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: refactor vua.
- Ly do:
  - UI/radio/checkbox/progress co the giu nguyen.
  - Step config va submit flow nen tach thanh data + API.
- Cach migrate cu the:
  - Port sang `src/pages/onboarding/OnboardingPage.tsx`.
  - Tach option arrays sang `src/data/onboarding.ts`.
  - Submit -> `POST /api/v1/onboarding/profile`.

## `app/pricing/page.tsx`

- Vai tro hien tai: pricing/plan comparison.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: sua nhe.
- Ly do:
  - UI cards/FAQ/CTA rat tot.
  - Billing state, CTA payment va feature arrays dang client-only.
- Cach migrate cu the:
  - Port sang `src/pages/marketing/PricingPage.tsx`.
  - Plans/features co the lay tu API pricing sau.
  - Register plan param -> query param React Router.

## `app/pricing/layout.tsx`

- Vai tro hien tai: metadata wrapper cho pricing.
- Muc do phu thuoc Next.js: cao.
- Kha nang tai su dung: thap.
- Hanh dong de xuat: thay hoan toan.
- Ly do: metadata layout la Next-only.
- Cach migrate cu the:
  - Dua metadata vao document meta handling.
  - Khong can mot layout rieng neu marketing layout da du.

## `app/(dashboard)/layout.tsx`

- Vai tro hien tai: dashboard sidebar, topbar, navigation.
- Muc do phu thuoc Next.js: cao.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: refactor vua.
- Ly do:
  - JSX layout rat reusable.
  - Phu thuoc chinh la `next/link` va `usePathname`.
  - Fake user summary va search moi o muc presentational.
- Cach migrate cu the:
  - Port sang `src/layouts/DashboardLayout.tsx`.
  - `usePathname` -> `useLocation`.
  - `Link href` -> `NavLink`/`Link`.
  - User/profile data -> lay tu `GET /api/v1/users/me`.

## `app/(dashboard)/dashboard/page.tsx`

- Vai tro hien tai: tong quan + bai chuan doan.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: vua.
- Hanh dong de xuat: refactor vua.
- Ly do:
  - UI co the giu.
  - `sampleQuestions` la mock domain data.
- Cach migrate cu the:
  - Tach sample data.
  - Goi API dashboard summary + diagnostic question session.

## `app/(dashboard)/practice/page.tsx`

- Vai tro hien tai: practice builder.
- Muc do phu thuoc Next.js: thap-vua.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: sua nhe.
- Ly do:
  - Chi can doi router va data source.
  - Card tree, toggle logic, filter controls co the giu nguyen.
- Cach migrate cu the:
  - Port sang `src/pages/practice/PracticePage.tsx`.
  - `TOEIC_PARTS` -> API catalog.
  - Start practice -> tao session backend.

## `app/(dashboard)/practice/runner/page.tsx`

- Vai tro hien tai: practice runner.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: vua.
- Hanh dong de xuat: refactor vua.
- Ly do:
  - UI can giu vi day la man hinh core.
  - `sampleQuestions` la mock; timer, answer state, explanation mode can doi sang session-driven.
- Cach migrate cu the:
  - Port layout gan nhu nguyen ven.
  - Lay session detail tu API.
  - Autosave/submit answer qua service layer.

## `app/(dashboard)/practice/summary/page.tsx`

- Vai tro hien tai: tong ket practice.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: refactor vua.
- Ly do: UI rat tai su dung duoc, du lieu tong ket dang mock.
- Cach migrate cu the:
  - Doc data tu `submit practice` response hoac `GET practice sessions/:id/result`.

## `app/(dashboard)/mock-test/page.tsx`

- Vai tro hien tai: mock test builder.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: sua nhe.
- Ly do: UI cards, preset selectors, recent tests rat reuse duoc.
- Cach migrate cu the:
  - Port sang `src/pages/mock-test/MockTestPage.tsx`.
  - `recentTests` -> API history.
  - Full/mini/weekly presets -> backend generator endpoints.

## `app/(dashboard)/mock-test/runner/page.tsx`

- Vai tro hien tai: full mock test runner.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: vua.
- Hanh dong de xuat: refactor vua.
- Ly do:
  - UI quan trong va nen giu.
  - `mockQuestions` 200 cau la fake; co route `/mock-test/result` dang chua ton tai.
- Cach migrate cu the:
  - Port sau practice runner.
  - Session API phai ho tro timer, save state, flagged question, submit result.

## `app/(dashboard)/progress/page.tsx`

- Vai tro hien tai: progress analytics.
- Muc do phu thuoc Next.js: thap.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: sua nhe.
- Ly do: chu yeu la UI + data arrays.
- Cach migrate cu the:
  - Port gan nhu nguyen ven.
  - `scoreHistory`, `weeklyActivity`, `heatmap`, `skillProgress` -> analytics APIs.

## `app/(dashboard)/review/page.tsx`

- Vai tro hien tai: review, notebook, AI chat.
- Muc do phu thuoc Next.js: thap.
- Kha nang tai su dung: cao cho UI, vua cho logic.
- Hanh dong de xuat: refactor vua.
- Ly do:
  - Domain nay phong phu, can service layer ro.
  - Dang co mock review question, notebook va AI response.
- Cach migrate cu the:
  - Giu UI panels, tabs, toolbar, sheet.
  - Tach data layer sang `reviewService`, `notebookService`, `aiTutorService`.

## `app/(dashboard)/settings/page.tsx`

- Vai tro hien tai: profile, learning preferences, notifications, subscription.
- Muc do phu thuoc Next.js: thap.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: refactor vua.
- Ly do: UI tabs/radix forms reuse rat tot, nhung data dang hard-code.
- Cach migrate cu the:
  - Port gan nhu nguyen ven.
  - Tach thanh nhieu service theo section.

## `components/`

- Vai tro hien tai: shared components ngoai `ui`.
- Muc do phu thuoc Next.js: thap, tru `theme-provider.tsx` + `ui/sonner.tsx` can `next-themes`.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: giu nguyen.
- Ly do: day la kho tai san reuse trung tam.
- Cach migrate cu the:
  - Tiep tuc import truc tiep tu React app.
  - Sau khi migration on dinh moi can nhac doi sang `src/components`.

## `components/ui/`

- Vai tro hien tai: shadcn/ui va wrappers.
- Muc do phu thuoc Next.js: rat thap.
- Kha nang tai su dung: rat cao.
- Hanh dong de xuat: giu nguyen.
- Ly do: phan lon khong phu thuoc framework, dang la backbone cua UI.
- Cach migrate cu the:
  - Khong rewrite.
  - Chuyen sang React app import lai qua alias `@/components/ui/*`.
  - Chi can kiem tra `components/ui/sonner.tsx` va `theme-provider.tsx`.

## `hooks/`

- Vai tro hien tai: custom hooks dung chung.
- Muc do phu thuoc Next.js: khong co.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: giu nguyen.
- Ly do: `use-mobile`, `use-toast` doc lap framework.
- Cach migrate cu the:
  - Tiep tuc tai su dung trong React app.

## `lib/`

- Vai tro hien tai: utility functions.
- Muc do phu thuoc Next.js: khong co.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: giu nguyen.
- Ly do: `cn` la utility core cho class merge.
- Cach migrate cu the:
  - Giu `lib/utils.ts`.
  - Chua can doi sang `.js`.

## `public/`

- Vai tro hien tai: static assets.
- Muc do phu thuoc Next.js: khong co.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: giu nguyen.
- Ly do: Vite cung phuc vu static assets rat tot.
- Cach migrate cu the:
  - Giu file path nhu cu de tranh doi UI.

## `styles/globals.css`

- Vai tro hien tai: global styles cu/thu hai.
- Muc do phu thuoc Next.js: khong co.
- Kha nang tai su dung: vua.
- Hanh dong de xuat: giu tam, nhung khong dung lam source chinh.
- Ly do: co ve la phien ban song song/thu nghiem voi `app/globals.css`.
- Cach migrate cu the:
  - Chon `app/globals.css` lam single source of truth.
  - So sanh, hop nhat, roi retire `styles/globals.css`.

## `package.json`

- Vai tro hien tai: scripts Next + dependencies UI.
- Muc do phu thuoc Next.js: cao.
- Kha nang tai su dung: vua.
- Hanh dong de xuat: refactor vua.
- Ly do: can song song ho tro Next cu va React/Vite moi trong giai doan transition.
- Cach migrate cu the:
  - Them scripts `dev:react`, `build:react`, `preview:react`.
  - Giu scripts Next cu de rollback an toan.
  - Them `react-router-dom`, `vite`, `@vitejs/plugin-react`, `vite-tsconfig-paths`.

## `tsconfig.json`

- Vai tro hien tai: TypeScript config.
- Muc do phu thuoc Next.js: vua.
- Kha nang tai su dung: vua.
- Hanh dong de xuat: sua nhe.
- Ly do: co plugin Next va include `.next/types`.
- Cach migrate cu the:
  - Giu tam de repo chay song song.
  - Ve sau tach `tsconfig.next.json` va `tsconfig.react.json` neu can.

## `next.config.mjs`

- Vai tro hien tai: Next build config.
- Muc do phu thuoc Next.js: cao.
- Kha nang tai su dung: thap.
- Hanh dong de xuat: thay hoan toan ve sau.
- Ly do: React/Vite khong dung file nay.
- Cach migrate cu the:
  - Giu nguyen trong giai doan transition.
  - Khi retire Next moi xoa.

## `components.json`

- Vai tro hien tai: shadcn config.
- Muc do phu thuoc Next.js: thap.
- Kha nang tai su dung: cao.
- Hanh dong de xuat: giu nguyen.
- Ly do: alias/components registry van dung duoc voi React app.
- Cach migrate cu the:
  - Sau nay cap nhat `tailwind.css` path neu can.

# PHAN 3 - Bang mapping migrate chi tiet

| Nguon hien tai | Dich sau migrate | Hanh dong | Ghi chu |
| -------------- | ---------------- | --------- | ------- |
| `app/layout.tsx` | `src/main.tsx` + `src/providers/AppProviders.tsx` | thay hoan toan | metadata/font/analytics doi cach lam |
| `app/globals.css` | `app/globals.css` | giu nguyen | Vite app import lai truc tiep |
| `app/page.tsx` | `src/pages/marketing/LandingPage.tsx` | sua nhe | doi `next/link`, tach data marketing |
| `app/onboarding/page.tsx` | `src/pages/onboarding/OnboardingPage.tsx` | refactor vua | submit sang onboarding API |
| `app/pricing/layout.tsx` | `src/router/meta/pricing.ts` hoac route meta utility | thay hoan toan | bo metadata convention cua Next |
| `app/pricing/page.tsx` | `src/pages/marketing/PricingPage.tsx` | sua nhe | giu card tree va FAQ |
| `app/(auth)/layout.tsx` | `src/layouts/AuthLayout.tsx` | sua nhe | nested auth routes |
| `app/(auth)/login/page.tsx` | `src/pages/auth/LoginPage.tsx` | sua nhe | fake login -> auth service |
| `app/(auth)/register/page.tsx` | `src/pages/auth/RegisterPage.tsx` | sua nhe | fake register -> auth service |
| `app/(auth)/forgot-password/page.tsx` | `src/pages/auth/ForgotPasswordPage.tsx` | sua nhe | fake forgot-password -> auth service |
| `app/(dashboard)/layout.tsx` | `src/layouts/DashboardLayout.tsx` | refactor vua | `usePathname` -> `useLocation` |
| `app/(dashboard)/dashboard/page.tsx` | `src/pages/dashboard/DashboardPage.tsx` | refactor vua | diagnostic sample questions -> API |
| `app/(dashboard)/practice/page.tsx` | `src/pages/practice/PracticePage.tsx` | sua nhe | part catalog -> API |
| `app/(dashboard)/practice/runner/page.tsx` | `src/pages/practice/PracticeRunnerPage.tsx` | refactor vua | session-driven |
| `app/(dashboard)/practice/summary/page.tsx` | `src/pages/practice/PracticeSummaryPage.tsx` | refactor vua | result data -> API |
| `app/(dashboard)/mock-test/page.tsx` | `src/pages/mock-test/MockTestPage.tsx` | sua nhe | builder + history -> API |
| `app/(dashboard)/mock-test/runner/page.tsx` | `src/pages/mock-test/MockTestRunnerPage.tsx` | refactor vua | 200 questions -> session API |
| `app/(dashboard)/progress/page.tsx` | `src/pages/progress/ProgressPage.tsx` | sua nhe | analytics data -> API |
| `app/(dashboard)/review/page.tsx` | `src/pages/review/ReviewPage.tsx` | refactor vua | review/notebook/AI -> APIs rieng |
| `app/(dashboard)/settings/page.tsx` | `src/pages/settings/SettingsPage.tsx` | refactor vua | profile/preferences/subscription -> API |
| `components/audio-player-bar.tsx` | `components/audio-player-bar.tsx` | giu nguyen | shared component tai dung truc tiep |
| `components/theme-provider.tsx` | `components/theme-provider.tsx` | giu nguyen | van dung duoc trong React app |
| `components/upgrade-pro-modal.tsx` | `src/components/billing/UpgradeProModal.tsx` | refactor vua | fake payment -> payment API |
| `components/ui/*` | `components/ui/*` | giu nguyen | chi patch neu co framework-specific edge |
| `hooks/use-mobile.ts` | `hooks/use-mobile.ts` | giu nguyen | no framework dependency |
| `hooks/use-toast.ts` | `hooks/use-toast.ts` | giu nguyen | no framework dependency |
| `lib/utils.ts` | `lib/utils.ts` | giu nguyen | khong nen doi sang `.js` luc nay |
| `public/*` | `public/*` | giu nguyen | preserve asset paths |
| `next.config.mjs` | `vite.config.ts` | bo dan | giu ca hai trong transition |
| `next-env.d.ts` | `vite-env.d.ts` | thay dan | hai file cung ton tai tam thoi |
| `package.json` | `package.json` | refactor vua | song song ho tro Next va React |

# PHAN 4 - Thiet ke cau truc moi

## Frontend React

- `src/pages`: page components theo route/domain.
- `src/layouts`: marketing, auth, dashboard layouts.
- `src/router`: router config va route metadata.
- `src/components`: component moi phat sinh trong React shell.
- `src/services`: API clients theo domain.
- `src/hooks`: hook moi dat rieng cho React app neu can.
- `src/data`: data tam trong giai doan migrate.
- `src/types`: shared frontend types.
- `src/providers`: theme, toast, query/auth providers.
- `src/styles`: font import, app shell styles.

## Backend FastAPI

- `backend/app/main.py`: app entry.
- `backend/app/api/routes`: route modules theo domain.
- `backend/app/schemas`: Pydantic request/response schemas.
- `backend/app/services`: business logic layer.
- `backend/app/models`: ORM models.
- `backend/app/core`: settings, security, auth utils.
- `backend/app/db`: session, base, migrations bootstrap.
- `backend/app/repositories`: query layer neu muon tach ro.
- `backend/tests`: API/service tests.

# PHAN 5 - Quy tac refactor bat buoc

- `next/link` -> `Link` hoac `NavLink` tu `react-router-dom`.
- `usePathname` -> `useLocation`.
- `window.location.href = "/..."` -> `useNavigate`.
- `next/font/google` -> import font qua CSS.
- `metadata`, `viewport`, `layout.tsx` cua Next -> `index.html` + React layouts + meta utility.
- `app/` route convention -> `src/pages` + `src/router`.
- Query string builder trong href -> `createSearchParams`/`useSearchParams`.
- Fake submit bang `setTimeout` -> service layer call API.
- Arrays hard-code cho domain data -> move sang backend endpoint hoac tam thoi `src/data/*`.
- UI components thuan -> giu nguyen toi da, uu tien TSX.
- File nen giu `.tsx`:
  - Toan bo `components/ui/*`.
  - Tat ca page co typed state, typed props, hoac generic component.
  - Layout dashboard/auth co typed navigation config.
- File co the dung `.jsx` ve sau:
  - Placeholder pages rat mong.
  - Presentational wrappers khong co typing phuc tap.
- Khong doi asset path neu khong bat buoc.
- Khong doi ten CSS variables/trang thai Tailwind neu khong can.

# PHAN 6 - Tach domain backend FastAPI

## Auth

- `POST /api/v1/auth/register`
  - Input: `name`, `email`, `password`, `plan?`
  - Output: `user`, `access_token`, `next_step`
  - Frontend: register page
- `POST /api/v1/auth/login`
  - Input: `email`, `password`
  - Output: `user`, `access_token`
  - Frontend: login page
- `POST /api/v1/auth/forgot-password`
  - Input: `email`
  - Output: `message`
  - Frontend: forgot-password page
- `POST /api/v1/auth/logout`
  - Input: refresh/session token
  - Output: `success`
  - Frontend: dashboard topbar, settings

## User/Profile

- `GET /api/v1/users/me`
  - Output: profile summary, plan, avatar, target score snapshot
  - Frontend: dashboard layout, settings
- `PATCH /api/v1/users/me`
  - Input: profile fields
  - Output: updated user
  - Frontend: settings/account
- `PATCH /api/v1/users/preferences`
  - Input: language, theme, audio, notification preferences
  - Output: updated preferences
  - Frontend: settings/experience, settings/notifications

## Onboarding

- `GET /api/v1/onboarding/options`
  - Output: levels, target scores, deadlines, study times, weak skills
  - Frontend: onboarding page
- `POST /api/v1/onboarding/profile`
  - Input: onboarding answers
  - Output: onboarding summary, roadmap draft id
  - Frontend: onboarding submit
- `POST /api/v1/onboarding/roadmap`
  - Input: onboarding profile id
  - Output: personalized roadmap
  - Frontend: onboarding success -> dashboard

## Dashboard

- `GET /api/v1/dashboard/overview`
  - Output: streak, target score, weekly progress, recommended next actions
  - Frontend: dashboard overview
- `GET /api/v1/dashboard/diagnostic-session`
  - Output: short diagnostic question set
  - Frontend: dashboard quick test widget

## Practice

- `GET /api/v1/practice/catalog`
  - Output: parts, skills, difficulties, counts
  - Frontend: practice builder
- `POST /api/v1/practice/sessions`
  - Input: selected parts, skill filter, difficulty, mode
  - Output: practice session id, metadata
  - Frontend: practice builder
- `GET /api/v1/practice/sessions/{session_id}`
  - Output: question list, progress, explanations availability
  - Frontend: practice runner
- `PATCH /api/v1/practice/sessions/{session_id}/answers`
  - Input: current answer map
  - Output: save status
  - Frontend: practice runner autosave
- `POST /api/v1/practice/sessions/{session_id}/submit`
  - Input: final answer map
  - Output: summary, skill breakdown, weaknesses
  - Frontend: practice summary

## Mock test

- `GET /api/v1/mock-tests/presets`
  - Output: full, mini, weekly presets
  - Frontend: mock-test builder
- `GET /api/v1/mock-tests/history`
  - Output: recent tests
  - Frontend: mock-test page
- `POST /api/v1/mock-tests/sessions`
  - Input: preset or custom config
  - Output: session id, duration, question counts
  - Frontend: mock-test builder
- `GET /api/v1/mock-tests/sessions/{session_id}`
  - Output: question navigator, timer state, current answers
  - Frontend: mock-test runner
- `PATCH /api/v1/mock-tests/sessions/{session_id}/answers`
  - Input: answer/flag payload
  - Output: save status
  - Frontend: mock-test runner
- `POST /api/v1/mock-tests/sessions/{session_id}/submit`
  - Input: final answers
  - Output: score, section breakdown, review payload
  - Frontend: mock-test result/review

## Progress analytics

- `GET /api/v1/progress/overview`
  - Output: current score, target, streak, days left
  - Frontend: progress page
- `GET /api/v1/progress/history`
  - Output: score history by week
  - Frontend: line chart
- `GET /api/v1/progress/skills`
  - Output: skill progress, part progress
  - Frontend: progress page
- `GET /api/v1/progress/activity`
  - Output: weekly minutes, heatmap
  - Frontend: progress page

## Review / notebook / saved items

- `GET /api/v1/review/questions`
  - Output: reviewed questions, filters, correctness
  - Frontend: review page
- `GET /api/v1/review/questions/{question_id}`
  - Output: detail, explanation, user answer, correct answer
  - Frontend: review detail panel
- `POST /api/v1/review/questions/{question_id}/notes`
  - Input: note text, tags
  - Output: saved note
  - Frontend: review page
- `GET /api/v1/notebook/items`
  - Output: notebook entries
  - Frontend: notebook sheet
- `POST /api/v1/notebook/items`
  - Input: word, meaning, example, tags
  - Output: created item
  - Frontend: review/notebook
- `POST /api/v1/ai/review-chat`
  - Input: question id, prompt
  - Output: AI explanation response
  - Frontend: review AI chat

## Subscription / pricing / payment

- `GET /api/v1/subscriptions/plans`
  - Output: free/pro plans, billing cycles, feature matrix
  - Frontend: pricing page
- `GET /api/v1/subscriptions/me`
  - Output: current plan, renewal info, status
  - Frontend: settings/subscription
- `POST /api/v1/payments/checkout`
  - Input: plan, billing cycle, payment method
  - Output: payment session, qr/url, expires_at
  - Frontend: pricing page, upgrade modal
- `GET /api/v1/payments/{payment_id}/status`
  - Output: pending/processing/success/failed
  - Frontend: upgrade modal polling
- `POST /api/v1/subscriptions/cancel`
  - Input: reason optional
  - Output: cancellation result
  - Frontend: settings/subscription

# PHAN 7 - Ke hoach migrate theo thu tu an toan

## Giai doan 1

- Lam gi: dung React shell moi.
- File/folder anh huong: `package.json`, `vite.config.ts`, `index.html`, `src/*`.
- Output mong doi: co the chay route React song song voi Next.
- Rui ro: dependency chua cai, alias/tsconfig can canh chinh them.

## Giai doan 2

- Lam gi: port shared components va utils tai su dung duoc.
- File/folder anh huong: `components/`, `components/ui/`, `hooks/`, `lib/`.
- Output mong doi: React app dung lai duoc design system hien co.
- Rui ro: toast/theme provider can kiem tra compatibility.

## Giai doan 3

- Lam gi: port pages tu Next sang React Router.
- File/folder anh huong: `app/page.tsx`, `app/(auth)/*`, `app/onboarding/*`, `app/pricing/*`, `app/(dashboard)/*`.
- Output mong doi: route parity o React app.
- Rui ro: logic local state va query params bi sai lech neu port qua nhanh.

## Giai doan 4

- Lam gi: thay cho phu thuoc Next.js.
- File/folder anh huong: tat ca `next/link`, `next/navigation`, metadata/layout, font import.
- Output mong doi: frontend khong con framework lock-in.
- Rui ro: active nav, scroll behavior, font rendering thay doi nhe.

## Giai doan 5

- Lam gi: tao service layer goi API.
- File/folder anh huong: `src/services/*`, `src/types/*`, `src/data/*`.
- Output mong doi: frontend khong con dung mock inline.
- Rui ro: schema mismatch trong giai doan backend chua on dinh.

## Giai doan 6

- Lam gi: scaffold FastAPI backend.
- File/folder anh huong: `backend/app/*`, `backend/tests/*`.
- Output mong doi: co bo khung router/schema/service/model theo domain.
- Rui ro: over-design som khi chua chot contract payload.

## Giai doan 7

- Lam gi: noi tung page voi backend that.
- File/folder anh huong: `src/pages/*`, `src/services/*`, `backend/app/api/routes/*`.
- Output mong doi: thay mock data bang live data theo domain.
- Rui ro: regression UI neu backend response khac ky vong.

# PHAN 8 - Sinh code theo tung dot

## Thu tu thuc hien

1. Tao cau truc frontend React moi.
2. Migrate router + layout.
3. Migrate shared components tai su dung duoc.
4. Migrate 2-3 page tieu bieu truoc.
5. Tao FastAPI skeleton.
6. Tao API client frontend.
7. Noi thu mot flow hoan chinh.

## Batch da generate trong repo o dot nay

- Da tao frontend React shell:
  - `index.html`
  - `vite.config.ts`
  - `vite-env.d.ts`
  - `src/main.tsx`
  - `src/providers/AppProviders.tsx`
  - `src/styles/fonts.css`
  - `src/layouts/*`
  - `src/router/index.tsx`
  - `src/pages/RoutePlaceholderPage.tsx`
  - `src/pages/NotFoundPage.tsx`
- Da cap nhat:
  - `package.json`
  - `.gitignore`
- Muc tieu cua batch nay:
  - Tao "duong ray moi" cho React/Vite.
  - Khong dong vao UI Next hien tai.
  - Giu route parity de batch sau port page vao dung dia chi.

## Assumptions hien tai

- Uu tien giu `.tsx` cho giai doan migrate vi repo dang co TypeScript san, UI components typed, va can giam regression.
- Chua xoa bat ky file Next nao.
- Chua scaffold FastAPI trong batch nay de giu dung thu tu migrate an toan va khong lam loang focus.
