/**
 * WhatsApp click-to-chat links (https://wa.me). Opens the customer's own WhatsApp
 * with a message already written, so a custom request reaches the bakery with
 * the details it needs — no account, API or app install on our side.
 */

export function whatsappLink(number: string | null | undefined, text: string) {
  if (!number) return null;
  const digits = number.replace(/\D/g, "");
  if (!digits) return null;
  return `https://wa.me/${digits}?text=${encodeURIComponent(text)}`;
}

export function productEnquiryText({
  name,
  size,
  choices,
  url,
}: {
  name: string;
  size?: string | null;
  choices?: string[];
  url?: string;
}) {
  const lines = [
    `Hi Leeza Cakes! I'd like something custom based on the ${name}.`,
    size ? `Size: ${size}` : null,
    choices?.length ? `So far I've picked: ${choices.join(", ")}` : null,
    "What I'd like to change: ",
    url ? `\n${url}` : null,
  ];
  return lines.filter(Boolean).join("\n");
}

export function orderEnquiryText(orderNumber: string) {
  return `Hi Leeza Cakes! I have a question about my order ${orderNumber}.\n\n`;
}

export const GENERAL_TEXT =
  "Hi Leeza Cakes! I'd like to ask about a cake that isn't on the website.\n\nOccasion:\nDate:\nServings:\nIdeas:";
