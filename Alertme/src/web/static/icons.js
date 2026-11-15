const paths = {
  overview:
    '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  list: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8m-8 4h8m-8 4h5"/>',
  building: '<path d="m2 8 10-6 10 6M3 9h18M5 10v9m5-9v9m4-9v9m5-9v9M2 22h20M2 19h20"/>',
  calendar:
    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 2v6m10-6v6M3 11h18m-12 4h2m3 0h2m-7 3h2"/>',
  bell: '<path d="M5 18h14l-2-4V9a5 5 0 0 0-10 0v5Zm5 4h4"/>',
  settings:
    '<path d="m10 3-1 3-3 1-3 3 2 3-1 4 4 2 2 3h4l2-3 4-2-1-4 2-3-3-3-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/>',
  logout: '<path d="M10 3H4v18h6m3-14 5 5-5 5M8 12h14"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  refresh: '<path d="M20 7A9 9 0 1 0 21 15M20 2v6h-6"/>',
  plus: '<path d="M12 4v16M4 12h16"/>',
  close: '<path d="m5 5 14 14M5 19 19 5"/>',
  arrow: '<path d="M6 18 18 6M6 6h12v12"/>',
  check: '<path d="m4 12 5 5L20 6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 3"/>',
  flag: '<path d="M5 22V3m0 0c5-4 9 4 15 0v11c-6 4-10-4-15 0"/>',
  edit: '<path d="m15 4 5 5M3 21l5-1L21 7a3 3 0 0 0-5-5L3 15v6Z"/>',
  trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
};
export const icon = (name) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.calendar}</svg>`;
