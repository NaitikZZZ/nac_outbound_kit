---
name: saaS-design-system
description: Enterprise marketplace & experience design system for SaaS marketing visuals. Use this skill whenever creating marketing illustrations for gift cards, rewards, travel, experiences, subscriptions, utilities, or any marketplace-based products. Includes five reusable composition patterns, photography direction by category, brand card rules, phone mockup guidelines, and storytelling formulas. Maintains premium, minimal visual language with 65% real photography and 35% UI, generous whitespace, floating modular cards, and one clear narrative per visual.
---

# SaaS Marketing Design Skill v3.0

## Product Marketplace & Experience Visual System

## Core Philosophy & Visual Equation

Every illustration follows this equation:

```
Real Product/Experience
        +
Simplified Product UI
        +
Floating Marketing Cards
        +
Premium Whitespace
        =
Enterprise SaaS Hero Visual
```

**Key insight:** The UI is always secondary. The product or experience is what users emotionally connect with.

**The objective:** Communicate ONE capability in under 5 seconds.

Every visual should answer:
> "What can this product do?"

not

> "What does this screen look like?"

---

# Design DNA: 10 Core Principles

## 1. White is the Hero

Whitespace dominates. The pages never feel colorful—they feel premium.

**Visual Composition Ratio:**
- **50%** White & Neutral (backgrounds, whitespace, cards, UI surfaces)
- **25%** Primary Blue (#1D4ED7) (brand identity, CTAs, primary objects)
- **15%** Yellow/Orange (#FF9501) (rewards, celebration, highlights, focal points)
- **5%** Green (#07B06F) (success indicators, achievements, positive metrics)
- **5%** Neutral Dark Grey (#0B0A08) (text, icons, shadows, supporting elements)

**Principle:** If a composition feels "too colorful," remove elements until white dominates.

---

## 2. Everything Floats

Nothing touches another element. Floating is achieved through positioning and layering, NOT rotation or distortion.

**What floating means:**
- Vertical offset (Y-axis movement)
- Horizontal offset (X-axis movement)
- Soft shadow underneath (elevation/depth)
- Layering above other elements (Z-depth)

**What floating does NOT mean:**
- ❌ No rotation (keep 0 degrees)
- ❌ No perspective transforms (keep flat)
- ❌ No skewing or distortion
- ❌ No 3D tilting
- ❌ No CSS transforms that deform the element

**Visual effect:** Elements appear to hover above the background, but maintain full structural integrity and visual strength.

Reference: Apple, Stripe, Linear (none use rotation for floating elements).

---

## 3. Cards Are the Building Blocks

Every illustration is assembled from independent UI cards, not monolithic designs.

**Examples of card types:**
- Dashboard
- Modal / Popup
- Mobile Screen
- Product Card
- Analytics Widget
- Notification
- Search Bar
- Category Tabs
- Reward Card

Instead of designing one large dashboard, design 5–8 independent floating cards that tell the story.

---

## 4. Layering Creates Depth

Almost every composition uses visual layering for storytelling:

```
Background
  ↓
Primary UI (largest, hero element)
  ↓
Floating UI (supporting cards)
  ↓
Popup / Modal
  ↓
Notification
  ↓
Confetti / Icon (accent)
```

This layering naturally guides the viewer's eye through the story.

---

## 5. UI Should Never Look "Complete"

Marketing visuals are NOT screenshots.

UI should be:
- Simplified
- Focused
- Clean
- Minimal
- Selective

**Rule:** Only include components needed for the story. Remove 70% of what a real UI would show. Keep the 30% that communicates the feature.

---

## 6. One Hero Feature Per Visual

Every image has ONE clear visual focus.

| Feature | Hero Element |
|---------|--------------|
| Rewards | Large Reward Card |
| Survey | Large Survey Widget |
| Marketplace | Product Grid |
| Recognition | Recognition Feed |
| Benefits | Benefit Cards |
| API | Code Snippet |

Everything else plays a supporting role.

---

## 7. Large Rounded Corners

Softness is a signature of this design language. Nothing is sharp.

| Element | Border Radius |
|---------|---------------|
| Cards | 20–28px |
| UI Components | 18–24px |
| Buttons | 14–18px |
| Search Inputs | 16–20px |

---

## 8. Very Soft Shadows

Not Material Design. Minimal elevation.

```
Vertical Offset:  12–24px
Blur Radius:      30–60px
Opacity:          8–15%
Color:            #000000 (black)
```

Shadows should be almost invisible unless you look for them.

---

## 9. Thin Borders Over Heavy Shadows

Use subtle borders instead of prominent shadows to maintain enterprise aesthetics.

```
Border Weight: 1px
Border Color:  #E6E5E3 (light grey)
```

This keeps the design premium and clean.

---

## 10. Product Screenshots Are Edited

Real screenshots are cluttered. Always edit them for marketing.

**What to remove:**
- Long tables
- Complex navigation menus
- Excessive UI elements
- Irrelevant sidebars

**Rule:** Crop aggressively. Show only the essential part that communicates the feature.

---

# Five Reusable Composition Patterns

These patterns are the backbone of marketplace & experience visuals. Choose the pattern that matches your product.

## Pattern 1: Mobile + Product Collection (Most Common)

**Used for:**
- Gift Cards
- Flights
- Hotels
- Experiences
- Subscriptions
- Utilities

**Structure:**
```
Mobile Screen (hero, left or center)
    +
Brand Cards / Product Cards (floating, right)
    +
Floating Success Card (optional, foreground)
```

**Narrative:** "See the mobile experience + the products available + the success outcome"

**Example:** Phone showing reward redemption → surrounding brand logos → "Reward Delivered" card floating above

---

## Pattern 2: Marketplace Grid

**Used for:**
- Product discovery
- Category browsing
- Catalog showcases

**Structure:**
```
Search Bar (top, large, rounded)
    ↓
Category Filter
    ↓
Product Grid (3–6 items)
    ↓
Floating Brand Logos (optional)
```

**Narrative:** "Browse and discover products easily"

**Rule:** Crop intentionally. Show only the browsing experience, not the entire application.

---

## Pattern 3: Lifestyle + Marketplace

**Used for:**
- Travel + airline brands
- Airport lounge experiences + airlines
- Premium experiential offerings

**Structure:**
```
Lifestyle Image (aspirational, hero element)
    +
Floating Brand Cards (overlaid or beside)
    +
Minimal UI (search, booking, or redemption)
```

**Narrative:** "Experience the lifestyle + access through our marketplace"

**Rule:** The lifestyle image is the emotional anchor. UI proves the capability.

---

## Pattern 4: Booking Flow

**Used for:**
- Hotel reservations
- Flight bookings
- Experience reservations

**Structure:**
```
Mobile Phone
    ↓
Large Hero Image (destination, hotel, or experience)
    ↓
Booking Form (lower half of phone)
    ↓
Brand Cards (floating, context)
```

**Narrative:** "See the destination + complete the booking + confirm success"

**Rule:** Keep the top 60% of the phone for the destination/hero image. Form occupies only the bottom 40%.

---

## Pattern 5: Product Journey (Timeline)

**Used for:**
- Redemption flows
- Subscription activation
- Success narratives

**Structure:**
```
Step 1: Progress / Selection
    ↓
Step 2: Confirmation / Order
    ↓
Step 3: Celebration / Success
```

**Narrative:** "Understand the entire workflow at a glance"

**Example:** "Select Reward" → "Confirm Details" → "Reward Delivered" (with celebration card)

---

# Marketplace Components

These components are the building blocks of marketplace patterns.

## Marketplace Product Cards

All product cards follow the same structure:

```
Image (primary, 70% of card height)
    ↓
Title (product name)
    ↓
Location / Brand (supporting text)
    ↓
CTA (blue button or link)
```

**Rules:**
- No unnecessary metadata
- No star ratings unless they directly add value
- Image is the focal point
- Consistent sizing across the grid

---

## Brand Cards

Brand cards are almost always:
- **Large** (120–160px per side)
- **Rounded** (24px border radius)
- **Flat colors** or logo only
- **Centered logo** on white background
- **Minimal border** (1px, #E6E5E3)
- **Equal spacing** between cards
- **One logo per card**

**CRITICAL:** Brand cards float, but maintain full strength:
- **NO rotation** (0 degrees, perfectly upright)
- **NO perspective distortion** (keep flat, not tilted)
- **NO skewing** (maintain rectangular integrity)
- **Straight alignment** at all times
- **Full visual strength** – cards feel solid and authoritative
- They float above other elements via soft shadows, not via rotation

**Floating position (not rotation):**
- Use Y-offset positioning (vertical displacement)
- Use X-offset positioning (horizontal displacement)  
- Use Z-depth (layering/shadow) to show floating
- Never use rotation, 3D perspective, or CSS transforms that distort

**Usage:** Surrounding product collections to show available brands (airlines, hotels, restaurants, utilities)

---

## Search Experience

Every marketplace begins with search. The search bar communicates discoverability.

**Structure:**
- **Large** (48–64px height)
- **Rounded** (18–20px border radius)
- **Soft border** (1px, #E6E5E3)
- **Placeholder text only** ("Search flights, hotels...")
- **Minimal filters** (avoid overwhelming options)
- **Search icon** (2px stroke, outlined)

**Visual principle:** The search bar is the entry point to exploration.

---

## Phone Mockups

Every phone mockup follows identical rules for consistency.

**Layout:**
```
Large top image (60% of screen)
    ↓
Content card (mobile UI, 30%)
    ↓
Large CTA button (blue, 10%)
    ↓
Minimal navigation (optional, 2–3 items only)
```

**Rules:**
- The phone isn't overloaded
- Only the feature being marketed is visible
- Navigation is minimal (no cluttered menus)
- Top image dominates the visual hierarchy
- CTA is large and blue

---

## Floating Success Cards

Floating cards communicate the outcome rather than the process.

**Examples:**
- "Reward Delivered"
- "Subscription Activated"
- "Booking Confirmed"
- "1000 Points Earned"
- "High Conversion"
- "Recharge Successful"

**Structure:**
```
Icon (blue or success-related)
    +
Bold headline
    +
Supporting text (optional)
```

**Visual principle:** These cards are intentionally separated from the main UI to emphasize the success outcome.

---

# Photography Direction

This is one of the strongest patterns in the design system. Photography quality directly impacts perceived enterprise value.

## By Category

### Gift Cards
- Logo only (premium brands)
- Consistent sizing
- White background

### Luxury Products
- Premium studio lighting
- Professional photography
- High contrast
- Jewel tones preserved

### Travel
- Editorial quality photography
- Wide-angle destination shots
- Vibrant, inviting
- Real locations (not generic)

### Hotels
- Luxury photography
- Room and lobby shots
- Lifestyle framing
- Professional lighting

### Food
- Warm natural lighting
- Appetizing close-ups
- Professional food photography
- Never stock images

### Sports & Recreation
- Action photography
- Motion captured
- Authentic moments
- Professional quality

### Events & Experiences
- Wide-angle venue shots
- Crowd/atmosphere
- Captured energy
- Professional documentation

---

## Photography Rules

**Never use:**
- Random stock photos
- Low-resolution images
- Overprocessed HDR
- Clipart
- Generic illustrations

**Always use:**
- Professional photography
- Real product/destination imagery
- Consistent style per category
- High resolution (2x or 3x for retina displays)
- Authentic representation

---

# Real Images vs UI Distribution

Across all marketplace visuals, maintain this ratio:

```
Real Photography: 65%
Product UI:       35%
```

**Principle:** The product experience sells the story. The UI proves the capability.

---

# Typography Hierarchy

Headings should be bold and simple. No decorative fonts.

| Level | Size | Use Case |
|-------|------|----------|
| Hero | 48–60px | Page headline |
| Section | 36–42px | Major section title |
| Widget | 28px | Card title |
| Card | 20–24px | Subheading |
| Body | 16–18px | Paragraph text |
| Caption | 14px | Supporting text, labels |

**Font:** Calibri or system sans-serif. Prioritize readability over uniqueness.

---

# UI Rules

## Icons

- **Style:** Outlined (not filled)
- **Stroke Weight:** 2px
- **Simplicity:** Minimal detail
- **Exception:** Fill only when necessary for emphasis or status indication

## Buttons

| Type | Style |
|------|-------|
| Primary | Blue (#1D4ED7) background, white text |
| Secondary | White background, blue (#1D4ED7) border |
| Ghost | Text only, no background or border |

## Cards

- **Background:** White (#FFFFFF)
- **Border:** 1px, #E6E5E3
- **Shadow:** Soft (12–24px offset, 30–60px blur, 8–15% opacity)
- **Corners:** 20–28px border radius

## Input Fields

- **Size:** Large, comfortable
- **Padding:** 16–20px (internal)
- **Border:** 1px, #E6E5E3
- **Focus State:** Blue border (#1D4ED7)

---

# Color Usage Guide

| Color | Primary Uses |
|-------|--------------|
| **Blue** (#1D4ED7) | Brand, navigation, buttons, charts, active tabs, CTAs |
| **Orange** (#FF9501) | Rewards, coins, recognition, celebration, gift cards, confetti, progress bars |
| **Green** (#07B06F) | Success states, completed actions, toggle switches, growth arrows, checkmarks |
| **Grey** (#57544F, #A7A29E, #E6E5E3) | Body text, disabled states, borders, supporting elements |
| **White** (#FFFFFF) | Backgrounds, cards, surfaces |
| **Neutral Dark** (#0B0A08) | Headings, heavy text, shadows |

---

# Spacing System

Whitespace is intentional and calculated.

| Element | Spacing |
|---------|---------|
| Outer Margin (page edge to content) | 64–96px |
| Between floating cards | 24–40px |
| Inside card container | 24–32px |
| Card padding (internal) | 32px |

**Rule:** More whitespace is always better. If you're unsure, add more.

---

# Storytelling Formula: One Capability Per Visual

Each marketplace visual should communicate exactly ONE capability. Choose the capability, then pick the matching pattern and example.

---

## Air Travel

**Capability:** Redeem rewards for flights

**Pattern:** Mobile + Product Collection (Pattern 1)

**Visual Composition:**
```
Phone (showing reward redemption)
    +
Airline brand logos (floating, context)
    +
Plane illustration (optional, supporting)
    +
Success card ("Flight booked!")
```

**Photography:** Airplane, destination, or flight cabin

---

## Hotel Booking

**Capability:** Book luxury hotels with points

**Pattern:** Booking Flow (Pattern 4)

**Visual Composition:**
```
Phone (top: hero hotel image, bottom: booking form)
    +
Hotel exterior photography (large)
    +
Hotel brand logos (floating)
    +
"Booking confirmed" card
```

**Photography:** Luxury hotel rooms, lobbies, destination

---

## Experiences & Entertainment

**Capability:** Redeem unforgettable experiences

**Pattern:** Lifestyle + Marketplace (Pattern 3)

**Visual Composition:**
```
Lifestyle image (concert, spa, adventure)
    +
Experience category cards (floating)
    +
"Experience unlocked" success card
```

**Photography:** Genuine experience moments, not staged

---

## Subscriptions

**Capability:** Use rewards for digital subscriptions

**Pattern:** Mobile + Product Collection (Pattern 1)

**Visual Composition:**
```
Phone (showing subscription activation)
    +
Brand logos (Netflix, Spotify, etc., floating)
    +
"Subscription activated" card
```

**Photography:** App logos, subscription service branding

---

## Utilities & Essentials

**Capability:** Pay everyday bills using rewards

**Pattern:** Mobile + Product Collection (Pattern 1)

**Visual Composition:**
```
Phone (showing bill payment)
    +
Utility provider logos (electricity, water, internet)
    +
"Payment successful" card
```

**Photography:** Minimal—focus on brand logos and phone UI

---

## Marketplace Discovery

**Capability:** Access a global catalog of products

**Pattern:** Marketplace Grid (Pattern 2)

**Visual Composition:**
```
Search bar (hero, top)
    ↓
Product grid (6–12 items)
    ↓
Brand logos (floating, context)
```

**Photography:** Product photography, merchandise, variety

---

## Gift Cards

**Capability:** Send rewards instantly as gift cards

**Pattern:** Mobile + Product Collection (Pattern 1)

**Visual Composition:**
```
Phone (showing gift card design)
    +
Brand cards (surrounding, showing options)
    +
"Gift sent!" notification
```

**Photography:** Gift card designs, premium brand logos

---

# Design Principles

## Principle 1: Show the Experience, Not the Interface

**Instead of:** Showing every UI detail, form field, and menu

**Show:**
- The product or experience (65% of visual)
- The UI that enables it (35% of visual)
- The emotional outcome (celebration, success)

Lifestyle imagery sells. UI proves it works.

---

## Principle 2: Photography is 65% of the Story

Real product and lifestyle photography is the hero of marketplace visuals.

**Examples:**
- A stunning hotel room photo sells "book hotels"
- Airline cabin photography sells "fly anywhere"
- Delicious food photo sells "dine out"
- Sports action photo sells "experience adventures"

UI is supporting evidence, not the main story.

---

## Principle 3: Brand Cards Create Context

Surrounding your mobile mockup or marketplace grid with brand logos immediately communicates "access to premium brands."

**Rule:** 3–6 large, well-spaced brand cards provide instant credibility without cluttering.

---

## Principle 4: One Capability Per Visual

Each visual should have a single, instantly understood message.

| Visual | Message |
|--------|---------|
| Phone + airlines + plane | "Redeem flights" |
| Hotel photo + booking form | "Book hotels with points" |
| Product grid + search | "Discover the marketplace" |
| Celebration card | "Reward delivered instantly" |

Clarity over complexity.

---

## Principle 5: Simplify to 30%

Real product UIs are cluttered. Marketing visuals are intentionally simplified.

**Rule:** Remove 70% of the actual UI. Keep only the 30% that communicates the feature.

For booking: Show only the destination photo + booking button. Hide menus, settings, navigation.

---

## Principle 6: Success Cards Celebrate Outcomes

Floating success cards aren't UI—they're emotional moments.

**Examples:**
- "Booking confirmed!"
- "Reward delivered!"
- "Subscription activated!"
- "1000 points earned!"

These cards float above other UI to emphasize the positive outcome.

---

## Principle 7: Layering Creates Depth & Story

Use visual layering to guide the eye through the narrative.

```
Layer 1: Background (subtle color or white)
Layer 2: Main UI (phone, marketplace grid, etc.)
Layer 3: Floating cards (brands, notifications)
Layer 4: Celebration (confetti, success card, icon)
```

Each layer adds emotional richness.

---

## Principle 8: Humans Appear Sparingly

When humans appear, they should be:
- Authentically representing their role (traveler, shopper, employee)
- Emotional and relatable (not generic stock photos)
- Minimal (usually just one person per visual)

Purpose: Create emotional connection without distracting from the product capability.

---

# Background & Environment

## Backgrounds

**Default:**
- #FAFAF8 (off-white) or pure white (#FFFFFF)

**Optional subtle enhancement:**
- Very soft radial glow (blue or orange) around the hero element
- Opacity: 5–10%
- Radius: 200–400px
- Nothing dramatic or distracting

## Product Photography

When including real product images (e.g., marketplace items):
- Use genuine product photography
- White background preferred
- Luxury lighting (professional)
- Never random stock images

---

# Motion (If Animated)

If visuals include animation:

**Allowed transitions:**
- Float (gentle upward/downward movement)
- Fade (opacity change)
- Slide (directional movement)
- Scale (grow/shrink)

**Avoid:**
- Bounce effects
- Excessive motion
- Rapid or jarring transitions

Motion should feel premium and intentional, never playful or careless.

---

# Summary: The Signature Style

If you had to describe this design language in one sentence:

> **"Enterprise SaaS marketing visuals built from simplified product interfaces, premium lifestyle photography, floating modular cards, generous whitespace, and a single, instantly understandable story."**

This system is scalable for rewards, recognition, employee engagement, gifting, travel, subscriptions, marketplaces, and related enterprise workflows.

---

# Design Checklist

Before finalizing any marketplace visual, verify:

**Photography & Content**
- [ ] Real photography dominates (65% of visual)
- [ ] Photography is professional quality for the category
- [ ] One clear capability is communicated (flight booking, hotel reservation, etc.)
- [ ] Human element enhances (not distracts from) the story

**Composition & Pattern**
- [ ] Visual follows one of the five reusable patterns
- [ ] One clear hero element (phone, marketplace grid, lifestyle image)
- [ ] Brand cards provide context (if applicable)
- [ ] Brand cards are STRAIGHT (0 degrees, no rotation)
- [ ] Brand cards are NOT distorted or skewed
- [ ] Brand cards float via positioning/shadow, NOT rotation
- [ ] Floating cards emphasize success outcome

**UI & Components**
- [ ] UI is simplified to 30% (70% removed)
- [ ] Phone mockup follows the rules (60% hero image, 30% content, 10% CTA)
- [ ] Product cards have consistent structure (image → title → location → CTA)
- [ ] Search bar is prominent and large (if marketplace)

**Visual Design**
- [ ] White/neutral dominates (50% of composition)
- [ ] All elements float (24–40px spacing between cards)
- [ ] Border radius is soft (20–28px cards, 18–24px components)
- [ ] Shadows are soft (8–15% opacity, 30–60px blur)
- [ ] Borders are thin (1px, #E6E5E3) when used

**Color & Typography**
- [ ] Colors follow the usage guide (blue dominant, orange accents, green for success)
- [ ] CTA buttons are large, blue, and rounded (14–18px radius)
- [ ] Typography hierarchy is clear (hero > section > body > caption)
- [ ] No more than 2–3 font sizes in one visual

**Storytelling**
- [ ] Visual answers one product question (What can users do?)
- [ ] Layering guides the eye (background → main UI → floating cards → celebration)
- [ ] Success/outcome is visually prominent
- [ ] No competing narratives

**Final Check**
- [ ] Does this visual communicate instantly (under 5 seconds)?
- [ ] Is this premium or does it feel generic/stock?
- [ ] Could a real customer understand the feature from this visual alone?
- [ ] Does this fit alongside other marketplace visuals?

---

# Next Steps

This skill will be expanded to include:

- **Figma Component Library** – Pre-built brand cards, phone mockups, product card templates
- **AI Prompt Framework** – Consistent prompts for generating marketplace-style visuals
- **Animation Guidelines** – Motion for card transitions, floating elements, success celebrations
- **Feature-Specific Templates** – Ready-to-adapt patterns for each marketplace category
- **Brand Consistency Audits** – Tools for verifying compliance with the system
- **Landing Page Modules** – Hero section compositions combining multiple marketplace patterns

For now, use this skill as your foundation for all SaaS marketplace and experience visual design.

