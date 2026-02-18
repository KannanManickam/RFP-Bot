# SparkToShip — Style Guide (Lite)

A minimal reference for sub-projects to maintain visual consistency without bloating the codebase.

---

## 1. Quick Setup

**Fonts**
Add to `index.html` `<head>`:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
```

**Tailwind Config (`tailwind.config.js`)**
Add this to your `extend` block:
```js
extend: {
  colors: {
    beige: '#f0efe7',      // Backgrounds
    charcoal: '#5a5a4a',   // Text & Headings
    orange: '#ff8c42',     // Primary Actions / Accents
    teal: '#50c8a3',       // Secondary / Success
    grid: '#e6e4d9',       // Borders & Dividers
  },
  fontFamily: {
    sans: ['Inter', 'sans-serif'],
    display: ['Space Grotesk', 'sans-serif'],
  },
  borderRadius: {
    lg: '0.75rem',
    md: 'calc(0.75rem - 2px)',
    sm: 'calc(0.75rem - 4px)',
  }
}
```

---

## 2. Core Colors

| Role | Color | Hex | Tailwind Class |
| :--- | :--- | :--- | :--- |
| **Background** | Beige | `#f0efe7` | `bg-beige` |
| **Text** | Charcoal | `#5a5a4a` | `text-charcoal` |
| **Accent/Button** | Orange | `#ff8c42` | `bg-orange` |
| **Secondary** | Teal | `#50c8a3` | `bg-teal` |
| **Border** | Grid Gray | `#e6e4d9` | `border-grid` |

---

## 3. Typography

*   **Headings (`h1-h6`)**: Use **Space Grotesk**.
    *   Example: `font-display font-bold text-charcoal`
*   **Body Text**: Use **Inter**.
    *   Example: `font-sans text-charcoal`

---

## 4. UI Components

### Buttons
*   **Primary**: Orange background, dark text, rounded-full (pill shape).
    *   `bg-orange text-charcoal rounded-full px-6 py-2 font-medium hover:opacity-90`
*   **Secondary**: Transparent background, charcoal border.
    *   `border border-charcoal text-charcoal rounded-full px-6 py-2 hover:bg-charcoal hover:text-beige`

### Cards
*   **Style**: White or Beige background, soft shadow, rounded corners.
    *   `bg-white rounded-lg border border-grid p-6 shadow-sm`

### Inputs
*   **Style**: Beige background, simple border.
    *   `bg-beige border-grid rounded-lg px-4 py-2 focus:ring-2 focus:ring-charcoal`
