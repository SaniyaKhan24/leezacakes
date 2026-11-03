"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { useMemo, useState } from "react";
import type { CakeExtras } from "@/components/cake/designs";
import {
  api,
  type CustomizationOption,
  type Product,
  type Selection,
} from "@/lib/api";
import { money } from "@/lib/format";

type Choice = { choiceIds: number[]; text: string };

/** Everything a customer can choose for one cake, plus the price and the 3D preview it implies. */
export function useCakeBuilder(product: Product | undefined) {
  const options = useQuery({
    queryKey: ["options", product?.slug],
    queryFn: () => api.options(product!.slug),
    enabled: Boolean(product),
  });
  const variants = useMemo(
    () =>
      (product?.variants ?? [])
        .filter((v) => v.is_active)
        .sort((a, b) => Number(a.price) - Number(b.price)),
    [product],
  );
  const [variantId, setVariantId] = useState<string | null>(null);
  const [picked, setChoices] = useState<Record<number, Choice>>({});
  const [quantity, setQuantity] = useState(1);
  const active = useMemo(
    () =>
      (options.data?.options ?? [])
        .filter((o) => o.is_active)
        .sort((a, b) => a.sort_order - b.sort_order),
    [options.data],
  );

  // Sensible defaults, derived rather than stored: the smallest size (below) and the
  // first choice of any required option. Option ids are per product, so switching
  // cakes naturally falls back to the new cake's defaults.
  const choices = useMemo(() => {
    const merged: Record<number, Choice> = {};
    for (const option of active) {
      const required =
        option.is_required && option.option.input_type === "single_choice";
      merged[option.id] = picked[option.id] ?? {
        choiceIds: required && option.choices[0] ? [option.choices[0].id] : [],
        text: "",
      };
    }
    return merged;
  }, [active, picked]);

  const variant = variants.find((v) => v.id === variantId) ?? variants[0];
  const extrasTotal = active.reduce((sum, option) => {
    const picked = choices[option.id]?.choiceIds ?? [];
    return (
      sum +
      option.choices
        .filter((c) => picked.includes(c.id))
        .reduce((s, c) => s + Number(c.price_adjustment), 0)
    );
  }, 0);
  const unit =
    Number(
      variant?.price ?? product?.effective_price ?? product?.base_price ?? 0,
    ) + extrasTotal;

  const missing = active.filter((o) => {
    const c = choices[o.id];
    if (!o.is_required) return false;
    return o.option.input_type === "text"
      ? !c?.text.trim()
      : !(c?.choiceIds.length ?? 0);
  });

  const selections: Selection[] = active.flatMap((option): Selection[] => {
    const c = choices[option.id];
    if (!c) return [];
    // The cart validates against the global option and choice ids, not the per-product rows.
    if (option.option.input_type === "text")
      return c.text.trim()
        ? [{ option_id: option.option.id, text_value: c.text.trim() }]
        : [];
    const choiceIds = option.choices
      .filter((ch) => c.choiceIds.includes(ch.id))
      .map((ch) => ch.choice);
    return choiceIds.length
      ? [{ option_id: option.option.id, choice_ids: choiceIds }]
      : [];
  });

  const nameOf = (option: CustomizationOption, ids: number[]) =>
    option.choices
      .filter((ch) => ids.includes(ch.id))
      .map((ch) => ch.choice_name);
  const extras: CakeExtras = { touches: [], candles: "none" };
  for (const option of active) {
    const c = choices[option.id];
    if (!c) continue;
    const slug = option.option.slug;
    if (option.option.input_type === "text" && slug.includes("message"))
      extras.message = c.text;
    if (slug.includes("finishing") || slug.includes("touch"))
      extras.touches = nameOf(option, c.choiceIds);
    if (slug.includes("candle")) {
      const name = nameOf(option, c.choiceIds)[0]?.toLowerCase() ?? "";
      extras.candles = name.includes("sparkler")
        ? "sparkler"
        : name.includes("number")
          ? "number"
          : "none";
    }
  }
  const sizeIndex = Math.max(
    0,
    variants.findIndex((v) => v.id === variant?.id),
  );
  extras.scale =
    variants.length > 1 && !(product?.slug ?? "").includes("tier")
      ? [0.9, 1, 1.08][Math.min(2, sizeIndex)]
      : 1;

  return {
    options,
    active,
    variants,
    variant,
    setVariantId,
    choices,
    setChoices,
    quantity,
    setQuantity,
    unit,
    missing,
    selections,
    extras,
  };
}

export type Builder = ReturnType<typeof useCakeBuilder>;

export function SizePicker({ builder }: { builder: Builder }) {
  if (builder.variants.length === 0) return null;
  return (
    <fieldset className="option-group">
      <legend>
        Size <small>{builder.variants.length} options</small>
      </legend>
      <div className="option-grid">
        {builder.variants.map((v) => (
          <button
            key={v.id}
            type="button"
            className={`option-card ${builder.variant?.id === v.id ? "is-selected" : ""}`}
            onClick={() => builder.setVariantId(v.id)}
            aria-pressed={builder.variant?.id === v.id}
          >
            <span className="tick" aria-hidden="true" />
            <strong>{v.name.split("·")[0].trim()}</strong>
            <span>{v.name.split("·").slice(1).join("·").trim() || " "}</span>
            <span className="tabular">{money(v.price)}</span>
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export function OptionFields({ builder }: { builder: Builder }) {
  const { active, choices, setChoices } = builder;
  return (
    <>
      {active.map((option) => {
        const current = choices[option.id] ?? { choiceIds: [], text: "" };
        const type = option.option.input_type;
        const max =
          option.max_selections ??
          (type === "single_choice" ? 1 : option.choices.length);
        const toggle = (id: number) => {
          setChoices((prev) => {
            const picked = (prev[option.id] ?? current).choiceIds;
            let next: number[];
            if (type === "single_choice")
              next = picked.includes(id) && !option.is_required ? [] : [id];
            else if (picked.includes(id)) next = picked.filter((x) => x !== id);
            else
              next =
                picked.length >= max
                  ? [...picked.slice(1), id]
                  : [...picked, id];
            return {
              ...prev,
              [option.id]: {
                ...prev[option.id],
                choiceIds: next,
                text: prev[option.id]?.text ?? "",
              },
            };
          });
        };
        return (
          <fieldset className="option-group" key={option.id}>
            <legend>
              {option.option.name}
              <small>
                {option.is_required
                  ? "Required"
                  : type === "multiple_choice"
                    ? `Up to ${max}`
                    : "Optional"}
              </small>
            </legend>
            {type === "text" ? (
              <div className="message-input">
                <input
                  value={current.text}
                  maxLength={32}
                  placeholder="Happy birthday, Meera"
                  onChange={(e) =>
                    setChoices((prev) => ({
                      ...prev,
                      [option.id]: { choiceIds: [], text: e.target.value },
                    }))
                  }
                  aria-label={option.option.name}
                />
                <small className="tabular">{current.text.length}/32</small>
              </div>
            ) : (
              <div className="option-grid">
                {option.choices
                  .filter((c) => c.is_active)
                  .map((choice) => {
                    const selected = current.choiceIds.includes(choice.id);
                    return (
                      <motion.button
                        key={choice.id}
                        type="button"
                        whileTap={{ scale: 0.97 }}
                        className={`option-card ${selected ? "is-selected" : ""}`}
                        onClick={() => toggle(choice.id)}
                        aria-pressed={selected}
                      >
                        <span className="tick" aria-hidden="true" />
                        <strong>{choice.choice_name}</strong>
                        <span className="tabular">
                          {Number(choice.price_adjustment) > 0
                            ? `+ ${money(choice.price_adjustment)}`
                            : "Included"}
                        </span>
                      </motion.button>
                    );
                  })}
              </div>
            )}
          </fieldset>
        );
      })}
    </>
  );
}
