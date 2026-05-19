# 03 — Mobile UX Plan

> **Phase 1 — Mobile Migration Audit**
> Generated: 2026-05-13 | Status: Complete

---

## 1. UI Elements to Keep from Web

These elements translate well to mobile and should maintain the same **functionality** (not necessarily the same visual layout):

| Element | Web Implementation | Keep for Mobile | Adaptation |
|---------|-------------------|----------------|------------|
| Color system | Primary brand colors, dark/light theme | ✅ Yes | Use same palette via `ThemeData` |
| Card-based layouts | shadcn/ui cards with borders + shadows | ✅ Yes | Flutter `Card` with same border radius |
| Score circles/badges | Accuracy %, score numbers | ✅ Yes | `CircularProgressIndicator` or custom painter |
| Progress bars | Linear progress for parts/weeks | ✅ Yes | `LinearProgressIndicator` |
| Charts | Recharts (bar, line) | ✅ Yes | `fl_chart` package (native Flutter) |
| Toast notifications | Sonner toasts | ✅ Yes | `SnackBar` or `fluttertoast` |
| Loading states | Loader2 spinner + text | ✅ Yes | `CircularProgressIndicator` + shimmer |
| Error states | Empty state with icon + message | ✅ Yes | Custom `EmptyState` widget |
| Icon system | Lucide icons | ✅ Yes | Use `lucide_icons` Flutter package or Material Icons |
| i18n | LanguageContext (EN/VI) | ✅ Yes | `flutter_localizations` + ARB files |

---

## 2. UI Elements to Redesign for Mobile

| Element | Web Design | Mobile Redesign | Reason |
|---------|-----------|----------------|--------|
| **Sidebar navigation** | 264px fixed sidebar | Bottom navigation bar (5 tabs) | No sidebar on mobile |
| **Top header bar** | Search + Bell + User dropdown | App bar with avatar + notification icon | Simpler mobile header |
| **Search** | Desktop search input in header | Search screen or search bar in app bar | Dedicated search UX |
| **Question runner layout** | Side-by-side (question + passage) | Stacked vertical or tabbed (passage/question) | Limited screen width |
| **Review page filters** | Horizontal tab bar + dropdowns | Bottom sheet filter picker or chip row | Touch-friendly filters |
| **Settings page** | Multi-tab layout in one page | Separate settings screens via list tiles | Native iOS/Android settings pattern |
| **Pricing page** | Horizontal plan comparison cards | Vertical swipeable plan cards | One plan per viewport |
| **AI Chat** | Right-side panel/drawer | Full-screen chat or bottom sheet | Mobile chat UX pattern |
| **Selection translator** | Text selection + popup | Long-press context menu | Native mobile interaction |
| **Highlight system** | Mouse text selection + color picker | Simplified tap-to-highlight | Touch is less precise than mouse |
| **Dropdown menus** | Radix dropdown menu | `BottomSheet` or `CupertinoActionSheet` | Native mobile pattern |

---

## 3. Bottom Navigation Plan

### Tab Layout

```
┌────────────────────────────────────────────┐
│                                            │
│            [Screen Content]                │
│                                            │
├────────┬────────┬────────┬────────┬────────┤
│  Home  │Practice│Progress│ Review │  More  │
│   🏠   │   📝   │   📊   │   🔄   │   ☰   │
└────────┴────────┴────────┴────────┴────────┘
```

### Tab Definitions

| Tab | Label | Icon | Root Screen | Sub-screens (push) |
|-----|-------|------|------------|---------------------|
| **Home** | Home | `Icons.home` | DashboardScreen | PlacementTest, MockTest catalog, WeeklyCheck |
| **Practice** | Practice | `Icons.edit_note` | PracticeScreen | PracticeRunner, PracticeSummary |
| **Progress** | Progress | `Icons.bar_chart` | ProgressScreen | Roadmap detail |
| **Review** | Review | `Icons.rate_review` | ReviewScreen | Review detail, Review-focus practice |
| **More** | More | `Icons.menu` | MoreScreen | Settings, Flashcards, Pricing, AI Chat, Roadmap |

### State Preservation

- Each tab maintains its own `Navigator` stack (using `IndexedStack` or `AutoRoute` nested navigation)
- Switching tabs preserves scroll position and state
- Practice runner is a **full-screen pushed route** (no bottom nav visible during practice)

---

## 4. Practice Runner UX

> **The most critical screen.** Web implementation is 59KB. Must be exceptionally well-designed for mobile.

### Layout

```
┌──────────────────────────────┐
│ ← Back    Q 3/30    ⏱ 12:34 │  ← App bar: back, progress, timer
├──────────────────────────────┤
│                              │
│ [Audio Player ▶ ━━━━━━━━━]  │  ← Audio (if listening)
│                              │
│ ┌──────────────────────────┐ │
│ │ Passage text / Image     │ │  ← Scrollable passage area
│ │ (expandable)             │ │
│ └──────────────────────────┘ │
│                              │
│ What does the speaker mean?  │  ← Question text
│                              │
│ ○ (A) Option text           │  ← Radio buttons (large touch targets)
│ ○ (B) Option text           │
│ ○ (C) Option text           │
│ ○ (D) Option text           │
│                              │
├──────────────────────────────┤
│ 🚩 Flag   [Prev] [Next ▸]   │  ← Bottom action bar
└──────────────────────────────┘
```

### Key Mobile Adaptations

- **Swipe gesture**: Swipe left/right to navigate between questions
- **Audio controls**: Floating audio player for listening sections
- **Passage viewer**: Expandable/collapsible with pinch-to-zoom for images
- **Large touch targets**: Minimum 48dp for option buttons
- **Question navigator**: Horizontal scrolling number pills at top, or bottom sheet grid
- **Auto-save**: Save progress on app background (lifecycle events)
- **Screen wake lock**: Keep screen on during practice
- **Haptic feedback**: Vibrate on answer selection and flag toggle

### Submission Flow

```
Practice → Timer ends / User submits
  → Confirmation dialog ("Submit 25/30 answers?")
  → POST /api/attempts/practice
  → Navigate to PracticeSummaryScreen
```

---

## 5. Review Center UX

### Layout

```
┌──────────────────────────────┐
│ Review Center         🔽     │  ← App bar + filter icon
├──────────────────────────────┤
│ [All] [Wrong] [Bookmarked]  │  ← Chip filter row (horizontal scroll)
│ [Noted] [Highlighted]       │
├──────────────────────────────┤
│ 📊 12 wrong · 5 bookmarked  │  ← Summary banner
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ Q.15 · Part 5 · ❌      │ │  ← Review item card
│ │ "The meeting was ___"    │ │
│ │ Your: (B) · Correct: (C) │ │
│ │ [📝 Note] [📌 Bookmark]  │ │
│ │ [📖 Explain] [🔄 Retry]  │ │
│ └──────────────────────────┘ │
│ ┌──────────────────────────┐ │
│ │ Q.22 · Part 3 · ❌      │ │
│ │ ...                      │ │
│ └──────────────────────────┘ │
└──────────────────────────────┘
```

### Interactions

- **Tap card**: Expand to show full explanation, passage, audio
- **Swipe right**: Mark as reviewed
- **Bookmark toggle**: Tap bookmark icon
- **Note editor**: Bottom sheet with text input
- **Retry button**: Opens PracticeRunner with review-focus questions
- **Source filter**: Bottom sheet with attempt type filters (practice/fulltest/minitest)

---

## 6. Dashboard UX

### Layout

```
┌──────────────────────────────┐
│ 🎯 GetGoals       🔔 [👤]   │  ← App bar with notification + avatar
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ Welcome back, Hoàng!     │ │  ← Greeting card
│ │ 🔥 5-day streak          │ │
│ │ Score: 450 → 600 target  │ │
│ └──────────────────────────┘ │
│                              │
│ ┌────────┐ ┌────────┐       │
│ │ 85%    │ │ 120min │       │  ← Quick stats grid (2x2)
│ │Accuracy│ │ Study  │       │
│ └────────┘ └────────┘       │
│ ┌────────┐ ┌────────┐       │
│ │ 12     │ │ 3      │       │
│ │Attempts│ │To Review│      │
│ └────────┘ └────────┘       │
│                              │
│ 📈 Weekly Activity           │  ← Bar chart (last 7 days)
│ [chart]                      │
│                              │
│ 🗺 Roadmap Progress          │  ← Roadmap summary card
│ Week 3 of 8 · In Progress   │
│ [View Roadmap →]             │
│                              │
│ 💡 Recommended Practice      │  ← AI recommendations
│ [Part 5 · Vocabulary Focus]  │
│ [Start →]                    │
└──────────────────────────────┘
```

---

## 7. Roadmap UX

### Layout

```
┌──────────────────────────────┐
│ ← Learning Roadmap           │
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ 8-Week TOEIC Roadmap     │ │  ← Roadmap header
│ │ Focus: Vocabulary (Part5) │ │
│ │ Based on: Diagnostic Test │ │
│ └──────────────────────────┘ │
│                              │
│ ● Week 1 ✅ Completed        │  ← Vertical timeline
│ │ Vocabulary Basics          │
│ │ 30 questions · 45 min      │
│ │                            │
│ ● Week 2 ✅ Completed        │
│ │ Grammar Focus              │
│ │                            │
│ ● Week 3 🔵 In Progress     │  ← Current week (expanded)
│ │ Reading Comprehension      │
│ │ ┌────────────────────────┐ │
│ │ │ Set 1: Main Idea (15q) │ │  ← Practice sets
│ │ │ [Start Practice →]     │ │
│ │ └────────────────────────┘ │
│ │ ┌────────────────────────┐ │
│ │ │ Set 2: Detail (10q)    │ │
│ │ │ ✅ 80% accuracy        │ │
│ │ └────────────────────────┘ │
│ │                            │
│ ○ Week 4 ⬜ Not Started     │
│ │ ...                        │
└──────────────────────────────┘
```

---

## 8. Progress UX

### Layout

```
┌──────────────────────────────┐
│ Progress                     │
├──────────────────────────────┤
│ [Overview] [Skills] [Parts]  │  ← Tab bar
├──────────────────────────────┤
│                              │
│ 📊 Overall Accuracy: 72%    │  ← Big number + ring chart
│                              │
│ 📈 Score Trend               │  ← Line chart
│ [chart: last 6 data points] │
│                              │
│ 📅 Weekly Activity           │  ← Bar chart
│ [chart: Mon-Sun minutes]     │
│                              │
│ Recent Practice              │  ← List
│ ┌──────────────────────────┐ │
│ │ Part 5 Practice · 85%    │ │
│ │ 20 questions · 12 min ago│ │
│ └──────────────────────────┘ │
│ ┌──────────────────────────┐ │
│ │ Mixed Practice · 68%     │ │
│ │ 30 questions · 2 hrs ago │ │
│ └──────────────────────────┘ │
└──────────────────────────────┘
```

---

## 9. AI Tutor UX

### Access Pattern

- **FAB (Floating Action Button)**: Present on Dashboard, Review, Practice Summary screens
- **Tap FAB**: Opens full-screen chat or bottom-sheet chat
- **Context-aware**: When opened from Review, pre-loads question context

### Chat Layout

```
┌──────────────────────────────┐
│ ← AI Tutor            ⋮     │
├──────────────────────────────┤
│                              │
│     🤖 "Hi! I can help     │
│     you understand any      │
│     TOEIC question."        │
│                              │
│ ┌──────────────────────────┐ │
│ │ Can you explain Q.15     │ │  ← User message
│ │ from my last practice?   │ │
│ └──────────────────────────┘ │
│                              │
│     🤖 "Sure! Question 15  │  ← AI response (SSE streamed)
│     tests vocabulary in     │
│     context..."             │
│                              │
├──────────────────────────────┤
│ [Type a message...]   [Send]│  ← Input bar
└──────────────────────────────┘
```

### SSE Implementation

- Use `dio` with `ResponseType.stream` or `eventsource_client` package
- Show typing indicator during streaming
- Parse SSE `data:` chunks and append to message

---

## 10. Payment/Pro UX

### Flow

```
More → Pricing → Select Plan → PayOS Checkout → Success/Cancel
```

### Mobile Adaptations

| Step | Implementation |
|------|---------------|
| Plan selection | Swipeable cards (monthly/quarterly/yearly) |
| Checkout | Open PayOS checkout URL in `InAppWebView` or external browser |
| Return URL | Use deep link `getgoals://payment-success?code=XXX` |
| Status polling | Poll `/api/payments/status/{code}` every 3s until paid/expired |
| Success | Show confetti animation + navigate to dashboard |
| Already Pro | Show plan details + expiry date + manage subscription |

### Backend Changes Needed

- Add `PAYOS_RETURN_URL_MOBILE` env var: `getgoals://payment-success`
- Add `PAYOS_CANCEL_URL_MOBILE` env var: `getgoals://payment-cancel`
- Modify `create_pro_order` to accept `platform` param and use mobile URLs

---

## 11. Loading / Empty / Error State Plan

### Loading States

| State | Component | Animation |
|-------|-----------|-----------|
| Screen loading | `ShimmerPlaceholder` | Skeleton cards with shimmer effect |
| List loading | `CircularProgressIndicator` | Centered spinner |
| Button loading | `ElevatedButton` with spinner | Replace text with small spinner |
| Pull-to-refresh | `RefreshIndicator` | Material pull-down indicator |
| Infinite scroll | `CircularProgressIndicator` at bottom | Load more spinner |

### Empty States

| Screen | Empty State Message | CTA |
|--------|-------------------|-----|
| Dashboard (new user) | "Welcome! Start with a placement test" | "Take Placement Test" |
| Practice (no data) | "Your TOEIC question bank is ready" | "Start Practicing" |
| Progress (no attempts) | "Complete your first practice to see progress" | "Go to Practice" |
| Review (no items) | "No items to review yet. Keep practicing!" | "Practice Now" |
| Roadmap (none) | "Generate a personalized learning roadmap" | "Generate Roadmap" |
| Flashcards (no topics) | "Flashcard topics are loading..." | Retry button |

### Error States

| Error Type | Display | Action |
|-----------|---------|--------|
| Network error | Snackbar + retry icon | "Retry" button |
| 401 Unauthorized | Redirect to login | Clear token, navigate to `/login` |
| 403 Pro required | Pro upgrade prompt | "Upgrade to Pro" CTA |
| 404 Not found | Inline error card | "Go Back" button |
| 500 Server error | Full-screen error | "Retry" button + "Report Issue" |
| Timeout | Snackbar | "Retry" button |
| No internet | Banner at top | "Tap to retry when online" |

### Offline Behavior

| Feature | Offline Strategy |
|---------|-----------------|
| Dashboard | Show cached data with "Last updated" timestamp |
| Practice | Block start (need questions from API) |
| In-progress practice | Auto-save answers locally, submit when back online |
| Flashcards | Cache topics + cards for offline study |
| Review | Show cached review items |
| Settings | Show cached preferences |
