# PDFCraft Enterprise Design System

## Product Vision & Brand Identity
PDFCraft is an enterprise-grade document engineering studio designed with pure white and soft sky-blue glassmorphism. It combines high-agency visual refinement, crystal-clear typography, spacious modern layouts, and subtle, non-intrusive motion to deliver an Apple-level and Linear-level product experience.

## Core Color Palette
- **Primary**: `#38BDF8` (Sky 400)
- **Secondary**: `#0EA5E9` (Sky 500)
- **Accent**: `#7DD3FC` (Sky 300)
- **Background**: `#F8FCFF` (Sky 50 Tint)
- **Surface**: `#FFFFFF`
- **Text Primary**: `#102A43` (Deep Navy)
- **Text Secondary**: `#52677D` (Slate Blue)
- **Text Muted**: `#627D98`
- **Text Subtle**: `#829AB1`
- **Border Default**: `rgba(56, 189, 248, 0.20)`
- **Border Hover**: `rgba(56, 189, 248, 0.38)`
- **Border Active**: `rgba(14, 165, 233, 0.55)`

## Glassmorphism Foundations
- **Translucent Layering**: Translucent white surfaces (`rgba(255, 255, 255, 0.78)` to `0.92`) with hardware-accelerated `backdrop-filter: blur(20px)` and `-webkit-backdrop-filter`.
- **Sky-Blue Accent Borders**: Refined 1px semi-transparent borders with subtle inner highlights (`inset 0 1px 0 rgba(255, 255, 255, 0.3)`).
- **Soft Ambient Shadows**: Multi-layered ambient drop shadows that diffuse light naturally without harsh dark patches:
  - Card Shadow: `0 12px 32px -8px rgba(14, 165, 233, 0.08), 0 4px 12px -2px rgba(16, 42, 67, 0.03)`
  - Raised Shadow: `0 18px 42px -10px rgba(14, 165, 233, 0.14), 0 6px 16px -2px rgba(16, 42, 67, 0.05)`
  - Modal Shadow: `0 24px 64px -12px rgba(16, 42, 67, 0.18), 0 8px 24px rgba(56, 189, 248, 0.12)`

## Typography & Sizing Principles
- **Font Stack**: `Plus Jakarta Sans`, `Inter`, `Manrope`, with system fallbacks.
- **Hierarchy Scale**:
  - Hero Titles: 36px – 42px (Font Weight: 800)
  - Section Headings: 24px – 28px (Font Weight: 700)
  - Card Headings: 18px – 20px (Font Weight: 600)
  - Stat Numbers: 38px – 44px (Font Weight: 800)
  - Body Copy: 15px – 16px (Line Height: 1.62)
  - Input Fields: 50px – 54px height, 15px font, comfortable 16px–48px padding
  - Buttons: 46px – 50px height, 15px font, 22px–26px horizontal padding
  - Table Rows: 78px – 82px minimum height, generous cell spacing, clear metadata hierarchy
  - Badges & Pills: 12px – 13px with clean uppercase tracking

## Non-Destructive Hover & Motion Philosophy
- **Zero Layout Shifts**: Strictly avoid sudden jumping, transform translateY shifts, dimension mutations, or scale jitter on hover.
- **Subtle Visual Feedback**: Hover states smoothly adjust background tint, border brightness, and ambient glow without altering position or dimensions.
- **Spring Curves & Easing**: Micro-transitions utilize `cubic-bezier(0.16, 1, 0.3, 1)` with durations between 160ms and 240ms.
- **Accessibility**: Full compliance with `prefers-reduced-motion: reduce`.

## Abstract Visual Assets
- Original high-resolution vector glass assets located in `app/static/img/abstract/`:
  - `sky-glass-waves.svg`: Translucent flowing gradient waves with frosted depth.
  - `geometric-orbs.svg`: 3D glass ring structures with diffused light orbs.
  - `crystal-prism.svg`: Minimalist geometric glass facets with prismatic refractions.
  - `fluid-mesh.svg`: Organic light diffusion gradients.
- Custom vector empty-state illustrations located in `app/static/img/illustrations/`:
  - `empty-documents.svg`
  - `empty-generated.svg`
  - `empty-history.svg`
  - `empty-merge.svg`

## Component Guidelines
- **Analytics & Telemetry**: Native responsive vector chart rendering 7-day throughput and operations distribution.
- **Upload Component**: Multi-stage progress visualizer with states for upload, signature verification, and preview rendering.
- **Workspace Editor**: High-density vector thumbnail grid with paginated batches (48 pages/batch), drag-and-drop output sequencing, and selection summary.
- **Merge Studio**: Multi-document selector with combined page counter, live sequence adjustment, and non-destructive output compilation.
