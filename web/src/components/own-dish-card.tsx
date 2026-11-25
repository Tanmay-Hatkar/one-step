"use client";

import { BookOpen, Check, CookingPot, X } from "lucide-react";
import Link from "next/link";

import { DishPhoto } from "@/components/dish-photo";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { agoLabel } from "@/lib/cooklog";
import type { UserDish } from "@/lib/types";

/** One of the user's own dishes as tonight's answer: what it is, when they last made it. */
export function OwnDishCard({
  dish,
  last,
  madeToday,
  onMade,
  onSkip,
}: {
  dish: UserDish;
  /** When they last cooked it, if it's on record. */
  last: Date | null;
  madeToday: boolean;
  onMade: () => void;
  onSkip: () => void;
}) {
  const id = dish.matched_dish_id;
  return (
    <Card className="gap-3 px-4 py-4">
      <p className="text-xs font-semibold tracking-wide text-primary uppercase">
        {madeToday ? "Made today" : "From your kitchen"}
      </p>
      <div className="flex items-center gap-3">
        {id ? (
          <DishPhoto id={id} name="" size={96} className="size-20 shrink-0 rounded-xl" />
        ) : null}
        <div className="min-w-0 flex-1 space-y-0.5">
          <h3 className="font-heading text-2xl leading-tight font-semibold tracking-tight">
            {dish.name}
          </h3>
          <p className="text-[15px] text-muted-foreground">
            {madeToday
              ? "Nice. It'll rest for a while before I suggest it again."
              : last
                ? `You last made it ${agoLabel(last)}.`
                : "Your usual. No surprises, no shopping."}
          </p>
        </div>
      </div>
      {dish.notes && !madeToday && (
        <p className="border-t pt-3 text-sm text-muted-foreground">{dish.notes}</p>
      )}
      {!madeToday && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={onMade} className="h-9">
            <CookingPot aria-hidden />
            I made this
          </Button>
          {id && (
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href={`/dish/${id}`} />}
              className="h-9"
            >
              <BookOpen aria-hidden />
              Recipe
            </Button>
          )}
          <Button variant="ghost" onClick={onSkip} className="h-9 text-muted-foreground">
            <X aria-hidden />
            Not tonight
          </Button>
        </div>
      )}
      {madeToday && (
        <p className="flex items-center gap-1.5 text-sm font-medium text-primary">
          <Check aria-hidden className="size-4" />
          Logged
        </p>
      )}
    </Card>
  );
}
