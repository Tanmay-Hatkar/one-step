// Applies follow-up answers to the kitchen. Mirrors `apply_patch` in the API.

import type { Have, Patch, Question, UserDish } from "./types";

const MAX_TECHNIQUES = 8;

/** One answer's effect, without modifying the inputs. */
export function applyPatch(
  dishes: UserDish[],
  have: Have,
  patch: Patch,
): { dishes: UserDish[]; have: Have } {
  let nextDishes = dishes;
  if (patch.dish !== null && patch.dish < dishes.length) {
    const dish = dishes[patch.dish];
    const techniques = [...new Set([...dish.techniques, ...patch.add_techniques])].slice(
      0,
      MAX_TECHNIQUES,
    );
    nextDishes = dishes.map((d, i) =>
      i === patch.dish ? { ...dish, techniques, protein: patch.protein ?? dish.protein } : d,
    );
  }
  const nextHave = patch.add_equipment.length
    ? { ...have, equipment: [...new Set([...have.equipment, ...patch.add_equipment])] }
    : have;
  return { dishes: nextDishes, have: nextHave };
}

/** Selected option indexes per question id. */
export type Answers = Record<string, number[]>;

/** The kitchen after every answer so far, in question order. Re-derived, so answers can change. */
export function applyAnswers(
  dishes: UserDish[],
  have: Have,
  questions: Question[],
  answers: Answers,
): { dishes: UserDish[]; have: Have } {
  let state = { dishes, have };
  for (const q of questions) {
    for (const index of answers[q.id] ?? []) {
      const option = q.options[index];
      if (option) state = applyPatch(state.dishes, state.have, option.patch);
    }
  }
  return state;
}
