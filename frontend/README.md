# Vysalytica Frontend

Modern React app built with Next.js 14, TypeScript, and Tailwind CSS.

## Project Structure

```
src/
├── app/
│   ├── layout.tsx      # Root layout with metadata
│   ├── page.tsx        # Home page
│   └── globals.css     # Global Tailwind styles
└── components/
    ├── Navbar.tsx      # Sticky navigation bar
    ├── Hero.tsx        # Hero section with CTA
    ├── Features.tsx    # Features grid container
    ├── FeatureCard.tsx # Individual feature card with hover effects
    └── Footer.tsx      # Footer with copyright
```

## Features

- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Modern Animations**: Framer Motion for smooth fade-in effects
- **TypeScript**: Full type safety
- **Next.js 14 App Router**: Latest React patterns
- **Tailwind CSS**: Utility-first styling with custom color palette

## Color Palette

- Primary Blue: `#2563eb`
- Accent Purple: `#7c3aed`
- Neutral Grays: `#111827` to `#f3f4f6`

## Getting Started

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm start
```

## Components

### Navbar
- Sticky positioning with shadow
- Logo on the left ("Vysalytica")
- Navigation links in the center (Features, Pricing, Partners)
- "Get Started" CTA button on the right
- Responsive (nav links hidden on mobile)

### Hero Section
- Centered headline with gradient text
- Subheadline with description
- Two CTA buttons: "Try Free Audit" (primary) and "Watch Demo" (outline)
- Fade-in animation with staggered children
- Gradient background

### Features Grid
- 3 columns (responsive: 1 column on mobile, 2 on tablet, 3 on desktop)
- Three feature cards with icons, titles, and descriptions:
  1. **QuickScan Audit** - Website visibility auditing
  2. **Citation Tracker** - AI citation monitoring
  3. **Answer Graph** - AI response visualization
- Each card has:
  - Subtle shadow with hover lift effect
  - Icon that scales on hover
  - "Learn More" link with arrow
  - Smooth animations

### Footer
- Centered copyright text
- Light gray background
- Minimal, clean design

## Button Actions

All buttons log to console:
- Navbar "Get Started" → `Button clicked: Get Started`
- Hero "Try Free Audit" → `Button clicked: Try Free Audit`
- Hero "Watch Demo" → `Button clicked: Watch Demo`
- Feature card "Learn More" → `Button clicked: Learn More - [Feature Title]`

## Technologies

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Animation library
- **React 18**: Latest React version

## Notes

- No backend integration (all buttons are placeholders)
- No forms or validation
- Single page application
- Only Tailwind utility classes used (no custom CSS files except globals.css)
