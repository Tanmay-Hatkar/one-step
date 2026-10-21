import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { ImageResponse } from "next/og";

export const alt =
  "One Step — you can already cook dishes you've never heard of.";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const DISHES = ["kabsa", "jambalaya", "paella_valenciana", "atkilt_wat"];

async function dataUri(file: string, type: string): Promise<string> {
  const bytes = await readFile(join(process.cwd(), file));
  return `data:${type};base64,${bytes.toString("base64")}`;
}

/** The share card for the home page (and any page without its own). */
export default async function Image() {
  const [icon, ...photos] = await Promise.all([
    dataUri("src/app/icon.svg", "image/svg+xml"),
    ...DISHES.map((d) => dataUri(`public/og/${d}.jpg`, "image/jpeg")),
  ]);
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: 72,
        background: "#fbf8f3",
        color: "#1c1814",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          color: "#b4532a",
        }}
      >
        <img src={icon} width={60} height={60} alt="" />
        <div style={{ fontSize: 38 }}>One Step</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ fontSize: 68, lineHeight: 1.05, letterSpacing: -2 }}>
          You can already cook dishes you&apos;ve never heard of.
        </div>
        <div style={{ fontSize: 30, color: "#6b6158" }}>
          Tell it what you cook. See dishes one step away, written as only
          what&apos;s different.
        </div>
      </div>
      <div style={{ display: "flex", gap: 20 }}>
        {photos.map((src, i) => (
          <img
            key={DISHES[i]}
            src={src}
            width={110}
            height={110}
            alt=""
            style={{ borderRadius: 24 }}
          />
        ))}
      </div>
    </div>,
    size,
  );
}
