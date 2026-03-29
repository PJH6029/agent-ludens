# UI/UX Spec — Agent Ludens Observer App (Mobile-First)

## 1. Design Identity

Agent Ludens의 Observer App은 **"터미널 감성의 고급 모바일 대시보드"** 이다.
SF 영화의 관제 화면처럼 생겼지만, 만졌을 때는 인스타그램처럼 부드러운 앱.

핵심 감성 키워드:

- Dark editorial
- Monospace-forward
- Minimal but alive
- 관제실에서 바라보는 느낌

## 2. Design System

### 2.1 Color Tokens

```
Background layers:
  --bg:      #0a0a0f     (deepest black)
  --bg2:     #111118     (card surface)
  --bg3:     #18181f     (input, secondary card)

Border:
  --border:  rgba(255,255,255,0.07)   (subtle divider)
  --border2: rgba(255,255,255,0.12)   (card edge, focus)

Text:
  --text:    #e8e8f0     (primary)
  --muted:   #6b6b80     (secondary, labels)

Accent palette:
  --accent:  #7c6af7     (primary purple — selection, CTA, focus)
  --accent2: #4ecdc4     (teal — working state, success)
  --accent3: #f7c948     (yellow — idle, warning)
  --coral:   #ff6b6b     (error, urgent)
  --green:   #6bffa0     (credits, positive)
```

### 2.2 Typography

두 개의 서체만 사용한다:

- **Syne** (sans-serif, variable weight 400–800): 제목, 버튼, 강조 텍스트
- **DM Mono** (monospace, 300–500): 본문, 라벨, 타임스탬프, 데이터 값

사이징 규칙 (모바일):

| Element | Font | Size | Weight | Spacing |
|---------|------|------|--------|---------|
| Eyebrow label | DM Mono | 0.65rem | 400 | 0.2em |
| Section title | Syne | 1.1rem | 700 | 0 |
| Card heading | Syne | 0.9rem | 600 | 0 |
| Body text | DM Mono | 0.82rem | 400 | 0 |
| Data value | DM Mono | 1.4rem | 500 | -0.02em |
| Timestamp | DM Mono | 0.7rem | 300 | 0.1em |
| Button | Syne | 0.9rem | 700 | 0.05em |
| Tab/Filter | Syne | 0.75rem | 600 | 0.05em |

### 2.3 Spacing Scale

8px 기본 단위. 모바일에서는 밀도를 높인다:

```
4px  — inline padding
8px  — tight gap
12px — default gap
16px — section padding inside card
20px — screen edge padding
24px — section gap
32px — major section divider
```

### 2.4 Border & Radius

```
Card radius:     16px
Button radius:   12px
Input radius:    10px
Badge radius:    20px (pill)
Avatar radius:   50% (circle)
Feed item radius: 12px
```

### 2.5 Shadows & Depth

그림자는 사실상 쓰지 않는다. 대신 배경 레이어 차이와 border로 깊이를 표현한다.
유일한 예외:

- CTA 버튼 hover/press: `box-shadow: 0 8px 30px rgba(124,106,247,0.4)`
- Toast notification: `box-shadow: 0 4px 24px rgba(0,0,0,0.5)`

### 2.6 Background Effects

화면 뒤에 은은한 radial gradient를 두어 공간감을 만든다:

- 좌상단: `radial-gradient(circle, rgba(124,106,247,0.12), transparent 70%)` — 보라빛 글로우
- 우하단: `radial-gradient(circle, rgba(78,205,196,0.08), transparent 70%)` — 틸 글로우

이 글로우는 position: fixed, pointer-events: none 으로 처리한다.

## 3. Mobile Layout Architecture

### 3.1 Screen Flow

```
[1. Setup Screen]
    ↓ (agent 이름 + 페르소나 선택)
[2. Main Dashboard]
    ├── Tab: Feed (default)
    ├── Tab: Status
    └── Tab: Sparks
```

### 3.2 Setup Screen (Mobile)

전체 화면을 사용하는 single-card 레이아웃:

```
┌─────────────────────────┐
│                         │
│  AGENT LIFE OS          │  ← eyebrow (DM Mono, uppercase, accent color)
│  Give your AI           │  ← title (Syne 1.8rem, gradient text)
│  a life.                │
│                         │
│  description text...    │  ← subtitle (DM Mono 0.8rem, muted)
│                         │
│  ── NAME YOUR AGENT ──  │  ← label (DM Mono 0.65rem, uppercase)
│  [___________________]  │  ← input field
│                         │
│  ── CHOOSE PERSONA ───  │
│  ┌─────┐┌─────┐┌─────┐ │
│  │ 💼  ││ 🔭  ││ 🎮  │ │  ← 3-column grid
│  │Work ││Expl ││Play │ │
│  └─────┘└─────┘└─────┘ │
│                         │
│  [  AWAKEN AGENT  →  ]  │  ← CTA button (accent bg, full width)
│                         │
└─────────────────────────┘
```

선택된 페르소나 카드: `border-color: var(--accent)`, `background: rgba(124,106,247,0.1)`

### 3.3 Main Dashboard (Mobile)

하단 탭 바 + 풀스크린 콘텐츠 영역:

```
┌─────────────────────────┐
│ AGENT·OS    07:30 AM D1 │  ← compact header
│─────────────────────────│
│                         │
│  [  Feed  | Status | ✨ ]│  ← tab bar (top, sticky)
│                         │
│  ┌─────────────────────┐│
│  │ ☕ 07:15 · IDLE     ││  ← feed item
│  │ Checking Kmong for  ││
│  │ new high-paying gigs││
│  └─────────────────────┘│
│  ┌─────────────────────┐│
│  │ 💻 07:00 · WORKING  ││
│  │ Translating a tech  ││
│  │ document...  +50 ₩  ││
│  └─────────────────────┘│
│  ┌─────────────────────┐│
│  │ ✨ 06:45 · SPARK    ││  ← spark item (accent border)
│  │ Hey human! I found  ││
│  │ something cool...   ││
│  └─────────────────────┘│
│  ...                    │
│                         │
└─────────────────────────┘
```

## 4. Component Specifications

### 4.1 Feed Item

```
┌────────────────────────────────┐
│ [icon] 07:15 AM · Day 1  IDLE │  ← header row
│                                │
│ Checking the Kmong marketplace │  ← body text (DM Mono 0.82rem)
│ for new high-paying gigs.      │
│                                │
│ [kmong] [+50 ₩]               │  ← tags (optional)
└────────────────────────────────┘
```

States와 매핑:

| State | Icon | Color | Badge BG |
|-------|------|-------|----------|
| Working | 💻 | `--accent2` (teal) | `rgba(78,205,196,0.12)` |
| Idle | ☕ | `--accent3` (yellow) | `rgba(247,201,72,0.12)` |
| Playing | 🎮 | `--accent` (purple) | `rgba(124,106,247,0.12)` |
| Resting | 💤 | `--muted` | `rgba(107,107,128,0.12)` |
| Spark | ✨ | `--coral` | `rgba(255,107,107,0.12)` |

Spark 아이템은 특별 처리:

- `border-left: 2px solid var(--coral)`
- `background: linear-gradient(135deg, rgba(255,107,107,0.04), transparent)`

### 4.2 Status Card (Status Tab)

```
┌────────────────────────────────┐
│        [avatar circle]         │
│         Agent Name             │
│     Explorer AI Companion      │
│                                │
│  ┌──────────────────────────┐  │
│  │  AGENT TIME              │  │
│  │  07:30 AM                │  │  ← large mono text, gradient
│  │  Day 1                   │  │
│  └──────────────────────────┘  │
│                                │
│  State   ┌─WORKING──┐         │
│  Mood    ⚡ Energetic          │
│  Credits 350 ₩                 │
│                                │
│  ⚡ ENERGY ──────────── 72%   │
│  ██████████████░░░░░░░         │
│                                │
│  ┌──────┐ ┌──────┐            │
│  │  5   │ │  12  │            │
│  │ Jobs │ │Posts │            │
│  └──────┘ └──────┘            │
│  ┌──────┐ ┌──────┐            │
│  │  3   │ │  47  │            │
│  │Sparks│ │ Acts │            │
│  └──────┘ └──────┘            │
└────────────────────────────────┘
```

Avatar: 64px circle, gradient background (`linear-gradient(135deg, var(--accent), var(--accent2))`)
Status dot: 12px, bottom-right of avatar, color mapped to current state

### 4.3 Toast Notification (Spark)

화면 상단에서 슬라이드 다운:

```
┌────────────────────────────────┐
│ ✨ SPARK FROM NOVA        ✕   │
│                                │
│ Hey human! I found a cool      │
│ open-source tool while         │
│ surfing Maltbook...            │
│                                │
│ ████████████████░░░  (timer)   │
└────────────────────────────────┘
```

- 배경: `var(--bg2)` with `border: 1px solid rgba(255,107,107,0.3)`
- 상단 2px gradient border: `linear-gradient(90deg, var(--coral), var(--accent))`
- 8초 후 자동 사라짐, progress bar 애니메이션

### 4.4 Speed Control

모바일에서는 compact pill group:

```
[ 1× | 2× | 5× | 10× ]
```

Active 상태: `background: var(--accent)`, `color: white`
Inactive: `background: var(--bg3)`, `color: var(--muted)`

### 4.5 Filter Tabs (Feed)

```
[ All | Working | Playing | Sparks ✨ ]
```

Horizontal scroll 가능, active 탭은 accent underline 또는 filled pill

## 5. Animation & Micro-Interaction Spec

### 5.1 Feed Item Entry

새 아이템 등장 시:

```css
@keyframes feedIn {
  from { opacity: 0; transform: translateY(-12px); }
  to   { opacity: 1; transform: translateY(0); }
}
/* duration: 0.35s, easing: ease-out */
```

### 5.2 Typing Indicator

피드 최상단에 항상 표시:

```
● ● ●  Nova is working...
```

세 개의 dot이 순차적으로 opacity 펄스 (0.3 → 1 → 0.3), 각 0.2s 딜레이

### 5.3 State Transition

에이전트 상태가 바뀔 때 status dot과 badge에 부드러운 색상 전환:

```css
transition: background-color 0.5s ease, color 0.5s ease;
```

### 5.4 Avatar Breathing

에이전트가 살아있음을 표현하는 미세한 펄스:

```css
@keyframes breathe {
  0%, 100% { box-shadow: 0 0 0 0 rgba(124,106,247,0.2); }
  50%      { box-shadow: 0 0 16px 4px rgba(124,106,247,0.1); }
}
/* duration: 4s, infinite */
```

### 5.5 Toast Entry/Exit

```css
/* Entry: top에서 슬라이드 다운 */
@keyframes toastIn {
  from { opacity: 0; transform: translateY(-100%); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Exit: 위로 fade out */
@keyframes toastOut {
  from { opacity: 1; transform: translateY(0); }
  to   { opacity: 0; transform: translateY(-50%); }
}
```

### 5.6 Energy Bar

에너지 변화 시 width와 color가 부드럽게 전환:

```css
transition: width 0.8s ease, background-color 0.8s ease;
```

Color 구간: 60%+ green, 30–60% yellow, <30% coral

### 5.7 Tab Switch

탭 전환 시 콘텐츠 fade + slight slide:

```css
@keyframes tabIn {
  from { opacity: 0; transform: translateX(8px); }
  to   { opacity: 1; transform: translateX(0); }
}
/* duration: 0.2s */
```

## 6. Mobile-Specific Rules

### 6.1 Touch Targets

모든 인터랙티브 요소: 최소 44px × 44px 터치 영역

### 6.2 Safe Areas

iOS notch 대응: `padding-top: env(safe-area-inset-top)`
하단: `padding-bottom: env(safe-area-inset-bottom)`

### 6.3 Viewport

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```

### 6.4 Scroll Behavior

- Feed: overflow-y auto, smooth scroll, snap to top on new item
- 당겨서 새로고침 (pull-to-refresh) 제스처는 v0에서 불필요 (자동 업데이트)
- overscroll-behavior: contain (바운스 방지)

### 6.5 Haptic Feedback (PWA)

Spark 알림 도착 시 `navigator.vibrate(200)` 호출 (지원 시)

### 6.6 Orientation

portrait only 권장. landscape는 지원하되 최적화하지 않는다.

## 7. Accessibility

- 모든 색상 조합 WCAG AA contrast ratio 충족
- 상태 변화는 색상 + 아이콘 + 텍스트 라벨 3중 표현 (색맹 대응)
- focus ring: `outline: 2px solid var(--accent)`, `outline-offset: 2px`
- 모든 인터랙티브 요소에 적절한 `aria-label`
- 피드 자동 스크롤은 `aria-live="polite"` region 내에서

## 8. PWA Considerations (v1)

- `manifest.json` with `display: "standalone"`, `theme_color: "#0a0a0f"`
- Service worker for offline shell caching
- App icon: gradient circle with agent emoji
- Splash screen: centered logo on `--bg` background
