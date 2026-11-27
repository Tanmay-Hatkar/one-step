// Server-safe: the inline <head> script that applies a hand-picked theme before first
// paint (no flash). Kept apart from theme.ts, which uses client-only React hooks.

export const THEME_KEY = "one-step:theme";

/** Must stay tiny and self-contained: it runs before anything else on the page. */
export const THEME_SCRIPT = `try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;
