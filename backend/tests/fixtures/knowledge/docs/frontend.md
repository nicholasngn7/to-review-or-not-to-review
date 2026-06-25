# Frontend rendering and UI state

This document covers the frontend: React components, rendering, local UI state, and
how user interface elements update when state changes.

## Components and state

A component reads its props and local state and renders markup. When state updates the
component re-renders. Keep derived values in memoized selectors to avoid extra renders.

## Buttons and layout

Buttons, panels, and layout containers are styled components. Avoid direct DOM mutation;
prefer declarative rendering driven by component state and props.
