(() => {
  const savedTheme = localStorage.getItem("dej-theme");
  const mode = ["light", "dark", "system"].includes(savedTheme) ? savedTheme : "system";
  const systemTheme = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";

  document.documentElement.dataset.theme = mode === "system" ? systemTheme : mode;
  document.documentElement.dataset.themeMode = mode;
})();