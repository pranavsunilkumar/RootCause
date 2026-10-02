import React, { useMemo, useState } from "react";

const RADIUS = { mastered: 16, weak: 12, unseen: 8 };
const COLOR = { mastered: "#7cc576", weak: "#f2b84b", unseen: "#6b665d" };
const LAYER_GAP = 130;
const ROW_GAP = 60;
const PAD = 40;

/**
 * concepts: [{id, name, prereqs: [id,...]}]
 * statusById: {id: "mastered"|"weak"|"unseen"}
 * onSelect: (conceptId) => void
 *
 * Node size reflects mastery scale (bigger = more mastered), positioned
 * left-to-right by dependency depth so prerequisites always sit to the
 * left of what they unlock -- the graph IS the curriculum structure.
 */
export default function ConceptMap({ concepts, statusById, onSelect }) {
  const [hover, setHover] = useState(null);

  const { nodes, edges, width, height } = useMemo(() => buildLayout(concepts), [concepts]);

  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={width} height={height} style={{ display: "block", minWidth: "100%" }}>
        {edges.map(([fromId, toId], i) => {
          const a = nodes[fromId], b = nodes[toId];
          if (!a || !b) return null;
          return (
            <line
              key={i}
              x1={a.x} y1={a.y} x2={b.x} y2={b.y}
              stroke="#2c2419" strokeWidth={1.5}
            />
          );
        })}
        {Object.values(nodes).map((n) => {
          const status = statusById[n.id] || "unseen";
          const r = RADIUS[status];
          return (
            <g
              key={n.id}
              transform={`translate(${n.x},${n.y})`}
              style={{ cursor: "pointer" }}
              onClick={() => onSelect?.(n.id)}
              onMouseEnter={() => setHover(n.id)}
              onMouseLeave={() => setHover(null)}
            >
              <circle r={r} fill={COLOR[status]} opacity={hover === n.id ? 1 : 0.85} />
              <text
                y={r + 14}
                textAnchor="middle"
                fontSize="10"
                fill={hover === n.id ? "#f4f1ea" : "#9e988e"}
              >
                {n.name}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function buildLayout(concepts) {
  const byId = Object.fromEntries(concepts.map((c) => [c.id, c]));

  // layer = 0 for roots, else 1 + max(layer of prereqs)
  const layer = {};
  function layerOf(id) {
    if (layer[id] !== undefined) return layer[id];
    const c = byId[id];
    layer[id] = c.prereqs.length === 0 ? 0 : 1 + Math.max(...c.prereqs.map(layerOf));
    return layer[id];
  }
  concepts.forEach((c) => layerOf(c.id));

  const byLayer = {};
  concepts.forEach((c) => {
    const l = layer[c.id];
    (byLayer[l] = byLayer[l] || []).push(c.id);
  });

  const nodes = {};
  Object.entries(byLayer).forEach(([l, ids]) => {
    ids.forEach((id, i) => {
      nodes[id] = {
        id,
        name: byId[id].name,
        x: PAD + Number(l) * LAYER_GAP,
        y: PAD + i * ROW_GAP + 10,
      };
    });
  });

  const edges = [];
  concepts.forEach((c) => c.prereqs.forEach((p) => edges.push([p, c.id])));

  const maxLayer = Math.max(...Object.values(layer));
  const maxRows = Math.max(...Object.values(byLayer).map((a) => a.length));

  return {
    nodes,
    edges,
    width: PAD * 2 + (maxLayer + 1) * LAYER_GAP,
    height: PAD * 2 + maxRows * ROW_GAP,
  };
}
