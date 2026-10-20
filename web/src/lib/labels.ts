// Readable names for vocabulary ids. Mirrors api/app/models/labels.py.

const TECHNIQUES: Record<string, string> = {
  marinate: "marinating",
  spice_paste: "spice paste",
  temper_spices: "blooming whole spices",
  sear: "searing",
  pan_fry: "pan-frying",
  stir_fry: "stir-frying",
  deep_fry: "deep-frying",
  roast: "roasting",
  grill: "grilling",
  braise: "braising",
  simmer: "simmering",
  steam: "steaming",
  boil: "boiling",
  bake: "baking",
  rice_in_stock: "rice cooked in stock",
  plain_rice: "plain rice",
  layered_dum: "layering and slow-steaming",
  scramble: "scrambling",
  knead_dough: "kneading dough",
  wrap_and_roll: "wrapping",
  poach: "poaching",
  blend_puree: "blending a sauce",
};

export function techniqueLabel(id: string): string {
  return TECHNIQUES[id] ?? id.replaceAll("_", " ");
}

export function equipmentLabel(id: string): string {
  return id.replaceAll("_", " ");
}
