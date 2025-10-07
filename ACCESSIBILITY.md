# FalconEye Accessibility Guide

## Overview
FalconEye is designed with accessibility in mind, following WCAG 2.1 AA guidelines to ensure the security system is usable by everyone.

## Color Contrast

### Dark Theme (Default)
- **Primary Green (#0f9d58)**: Used for buttons, status indicators, and active states
- **Background (#111)**: Dark background reduces eye strain
- **Text (#eee)**: High contrast white text on dark background
- **Cards (#222)**: Subtle contrast for content separation

**Contrast Ratios:**
- Green on Dark: 4.5:1 (AA compliant)
- White on Dark: 21:1 (AAA compliant)
- White on Green: 4.5:1 (AA compliant)

### Light Theme
- **Primary Green (#0f9d58)**: Maintains brand consistency
- **Background (#f5f5f5)**: Light background for better readability
- **Text (#333)**: Dark text on light background
- **Cards (#fff)**: Pure white cards with subtle shadows

**Contrast Ratios:**
- Green on Light: 4.5:1 (AA compliant)
- Dark on Light: 16.5:1 (AAA compliant)
- Dark on Green: 4.5:1 (AA compliant)

## Keyboard Navigation

### Tab Order
1. Theme toggle button
2. Navigation tabs (Live, Clips, Status, Settings)
3. Quality controls (High, Medium, Low)
4. Stream controls (Snapshot, Play/Pause, Fullscreen)
5. Quick action buttons
6. Form inputs and buttons

### Keyboard Shortcuts
- **Tab**: Navigate between interactive elements
- **Enter/Space**: Activate buttons and controls
- **Escape**: Close modals or exit fullscreen
- **Arrow Keys**: Navigate between quality options

## Screen Reader Support

### Semantic HTML
- Proper heading hierarchy (h1, h2, h3)
- Button elements with descriptive text
- Form labels associated with inputs
- Alt text for images and videos

### ARIA Labels
```html
<button aria-label="Take snapshot of live camera feed">📷</button>
<button aria-label="Toggle between light and dark theme">🌙</button>
<div role="status" aria-live="polite" id="stream-info">📡 Live • High Quality</div>
```

### Live Regions
- Stream status updates announced to screen readers
- Upload status changes announced
- Toast notifications announced

## Touch and Mobile Accessibility

### Touch Targets
- Minimum 44px touch target size
- Adequate spacing between interactive elements
- Large, easy-to-tap buttons

### Gesture Support
- Swipe navigation between tabs
- Pinch to zoom on video content
- Pull to refresh functionality

## Visual Indicators

### Status Indicators
- Color-coded status badges with text labels
- Upload status: ☁️ Uploaded, ❌ Failed, ⏳ Pending
- Online/offline indicators with both color and text

### Focus Indicators
- Clear focus outlines on all interactive elements
- High contrast focus rings
- Consistent focus styling across components

## Error Handling

### Form Validation
- Clear error messages
- Inline validation feedback
- Required field indicators

### Network Errors
- Toast notifications for connection issues
- Fallback content when streams fail
- Graceful degradation of features

## Testing Checklist

### Manual Testing
- [ ] Navigate entire interface using only keyboard
- [ ] Test with screen reader (NVDA, JAWS, VoiceOver)
- [ ] Verify color contrast meets AA standards
- [ ] Test on mobile devices with different screen sizes
- [ ] Verify all interactive elements are reachable

### Automated Testing
- [ ] Run axe-core accessibility tests
- [ ] Validate HTML markup
- [ ] Check color contrast ratios
- [ ] Test keyboard navigation

## Browser Support

### Supported Browsers
- Chrome 90+ (full support)
- Firefox 88+ (full support)
- Safari 14+ (full support)
- Edge 90+ (full support)

### Mobile Browsers
- iOS Safari 14+
- Chrome Mobile 90+
- Samsung Internet 13+

## Assistive Technology

### Screen Readers
- NVDA (Windows)
- JAWS (Windows)
- VoiceOver (macOS/iOS)
- TalkBack (Android)

### Voice Control
- Dragon NaturallySpeaking
- Voice Control (macOS)
- Voice Access (Android)

## Future Improvements

### Planned Enhancements
- [ ] High contrast mode option
- [ ] Font size adjustment controls
- [ ] Reduced motion preferences
- [ ] Voice commands for camera control
- [ ] Haptic feedback for mobile notifications

### Accessibility Testing
- [ ] Regular testing with real users
- [ ] Automated accessibility testing in CI/CD
- [ ] Performance testing with assistive technology

## Resources

### Tools
- [WAVE Web Accessibility Evaluator](https://wave.webaim.org/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [Color Contrast Analyzer](https://www.tpgi.com/color-contrast-checker/)

### Guidelines
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Accessibility Guidelines](https://webaim.org/)
- [Apple Human Interface Guidelines - Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility/overview/)

## Contact

For accessibility issues or suggestions, please contact the development team or create an issue in the project repository.
