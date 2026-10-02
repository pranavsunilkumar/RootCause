import React, { useEffect, useState, useRef, useMemo } from "react";
import * as THREE from "three";
import { api } from "../api.js";

// --- Rich Metadata for 3D Node Tooltips ---
const NODE_META = {
  vectors: { category: "Linear Algebra", desc: "Fundamental array of numbers representing magnitude and direction." },
  derivatives: { category: "Calculus", desc: "Instantaneous rates of change, serving as the core basis for optimization." },
  "probability-basics": { category: "Probability", desc: "Axioms of chance, normalizations, and expectation values." },
  "dot-product": { category: "Linear Algebra", desc: "Calculates directional projection and scalar affinity between vectors." },
  "partial-derivatives": { category: "Multivariable Calc", desc: "Rates of change across multivariable functions." },
  "chain-rule": { category: "Calculus", desc: "Rules governing derivatives of composite functions; essential for backprop." },
  softmax: { category: "Activation", desc: "Converts unbounded logits into calibrated probabilities summing to 1.0." },
  "matrix-multiplication": { category: "Linear Algebra", desc: "Linear transformation combining rows and columns." },
  "cosine-similarity": { category: "Vector Geometry", desc: "Measures pure angular alignment independent of vector magnitudes." },
  gradients: { category: "Calculus", desc: "Vector of partial derivatives pointing in the steepest ascent." },
  "computational-graphs": { category: "Autodiff", desc: "Directed graph tracking variables for automatic differentiation." },
  "cross-entropy": { category: "Loss Functions", desc: "Quantifies divergence between predicted probabilities and ground-truth." },
  "gradient-descent": { category: "Optimization", desc: "Iterative optimizer stepping opposite the gradient downhill." },
  backpropagation: { category: "Deep Learning", desc: "Reverse accumulation of loss gradients backwards through layers." },
  "linear-layer": { category: "Architecture", desc: "Dense affine transformation parameterized by learnable weights." },
  embeddings: { category: "Representation", desc: "Dense continuous vector lookups capturing latent semantics." },
  attention: { category: "Transformer Core", desc: "Dynamic querying mechanism weighting relevance between tokens." },
  "activation-functions": { category: "Non-Linearity", desc: "Enables deep networks to approximate non-linear boundaries." },
  "positional-encoding": { category: "Sequences", desc: "Injects sequence position ordering into permutation-invariant attention." },
  transformers: { category: "Architecture", desc: "Fully attention-driven sequence architecture." }
};

// --- 3D Concept Galaxy Component ---
function ThreeGalaxyMap({ concepts, statusById, onSelect }) {
  const containerRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  // Auto-calculate topological tiers for 3D layout
  const tieredConcepts = useMemo(() => {
    const nodes = concepts.map(c => ({ ...c, tier: 0, ...NODE_META[c.id] }));
    let changed = true;
    while (changed) {
      changed = false;
      for (const node of nodes) {
        if (!node.prereqs || node.prereqs.length === 0) continue;
        const maxPrereqTier = Math.max(...node.prereqs.map(pid => nodes.find(n => n.id === pid)?.tier || 0));
        if (node.tier <= maxPrereqTier) {
          node.tier = maxPrereqTier + 1;
          changed = true;
        }
      }
    }
    return nodes;
  }, [concepts]);

  // Generate Dependency Path Breadcrumbs (Root -> ... -> Target)
  const getBreadcrumbPath = (nodeId) => {
    const path = [];
    let current = tieredConcepts.find(c => c.id === nodeId);
    while (current) {
      path.unshift(current);
      if (!current.prereqs || current.prereqs.length === 0) break;
      current = tieredConcepts.find(c => c.id === current.prereqs[0]); // Follow primary prereq
    }
    return path;
  };

  useEffect(() => {
    if (!containerRef.current) return;
    const width = containerRef.current.clientWidth;
    const height = 500; // Fixed canvas height

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#0a0806");
    scene.fog = new THREE.FogExp2("#0a0806", 0.002);

    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 1500);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerRef.current.innerHTML = "";
    containerRef.current.appendChild(renderer.domElement);

    // Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const pointLight = new THREE.PointLight(0xf2b84b, 2, 500);
    pointLight.position.set(0, 50, 0);
    scene.add(pointLight);

    // Layout config
    const tierDepths = [-120, -50, 20, 90, 160, 230];
    const tierSpreads = [60, 80, 90, 80, 60, 30];
    const meshes = [];

    // Group and Position Nodes
    const tierGroups = {};
    tieredConcepts.forEach(c => {
      if (!tierGroups[c.tier]) tierGroups[c.tier] = [];
      tierGroups[c.tier].push(c);
    });

    Object.keys(tierGroups).forEach(tierStr => {
      const tier = parseInt(tierStr);
      const group = tierGroups[tier];
      const z = tierDepths[Math.min(tier, tierDepths.length - 1)];
      const radius = tierSpreads[Math.min(tier, tierSpreads.length - 1)];

      group.forEach((node, idx) => {
        const angle = (idx / group.length) * Math.PI * 2 + (tier * 0.5);
        node.pos = new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * (radius * 0.5) + ((idx % 2 === 0 ? 1 : -1) * 10), z);
        
        const status = statusById[node.id] || "unseen";
        const isMastered = status === "mastered";
        const isWeak = status === "weak";
        
        const color = isMastered ? 0x7cc576 : isWeak ? 0xf2b84b : 0x6b665d;
        const size = isMastered ? 6 : isWeak ? 5 : 4;

        const geo = new THREE.SphereGeometry(size, 24, 24);
        const mat = new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: isMastered ? 0.6 : 0.2 });
        const sphere = new THREE.Mesh(geo, mat);
        sphere.position.copy(node.pos);
        sphere.userData = { id: node.id, node };
        
        scene.add(sphere);
        meshes.push(sphere);

        // Add 3D Text Sprite
        const canvas = document.createElement('canvas');
        canvas.width = 256; canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.font = 'bold 22px Inter, sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillStyle = isMastered ? '#7cc576' : isWeak ? '#f2b84b' : '#9e988e';
        ctx.fillText(node.name, 128, 32);
        const tex = new THREE.CanvasTexture(canvas);
        const spriteMat = new THREE.SpriteMaterial({ map: tex });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(35, 8.5, 1);
        sprite.position.set(0, -size - 4, 0);
        sphere.add(sprite);
      });
    });

    // Draw Bézier Edges
    tieredConcepts.forEach(target => {
      if (!target.prereqs) return;
      target.prereqs.forEach(pid => {
        const source = tieredConcepts.find(c => c.id === pid);
        if (!source || !source.pos || !target.pos) return;
        
        const mid = source.pos.clone().lerp(target.pos, 0.5);
        mid.y += 20; // Arch upward

        const curve = new THREE.QuadraticBezierCurve3(source.pos, mid, target.pos);
        const points = curve.getPoints(20);
        const geo = new THREE.BufferGeometry().setFromPoints(points);
        
        const isMasteredEdge = (statusById[source.id] === "mastered" && statusById[target.id] === "mastered");
        const mat = new THREE.LineBasicMaterial({ 
          color: isMasteredEdge ? 0x4ade80 : 0x2c2419, 
          transparent: true, 
          opacity: isMasteredEdge ? 0.6 : 0.3 
        });
        scene.add(new THREE.Line(geo, mat));
      });
    });

    // Camera & Interaction
    let cameraTheta = Math.PI / 4;
    let cameraPhi = Math.PI / 3;
    let distance = 250;
    const targetCenter = new THREE.Vector3(0, 0, 0);

    const updateCam = () => {
      camera.position.x = targetCenter.x + distance * Math.sin(cameraPhi) * Math.sin(cameraTheta);
      camera.position.y = targetCenter.y + distance * Math.cos(cameraPhi);
      camera.position.z = targetCenter.z + distance * Math.sin(cameraPhi) * Math.cos(cameraTheta);
      camera.lookAt(targetCenter);
    };

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onClick = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const hits = raycaster.intersectObjects(meshes);
      if (hits.length > 0) {
        const clickedNode = hits[0].object.userData.node;
        setSelectedNode(clickedNode);
        // Gently fly camera to node
        targetCenter.copy(clickedNode.pos);
        distance = 120;
      }
    };

    renderer.domElement.addEventListener('click', onClick);

    let isDragging = false;
    let prevMouse = { x: 0, y: 0 };
    renderer.domElement.addEventListener('mousedown', (e) => { isDragging = true; prevMouse = { x: e.clientX, y: e.clientY }; });
    renderer.domElement.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      cameraTheta -= (e.clientX - prevMouse.x) * 0.01;
      cameraPhi = Math.max(0.1, Math.min(Math.PI - 0.1, cameraPhi - (e.clientY - prevMouse.y) * 0.01));
      prevMouse = { x: e.clientX, y: e.clientY };
    });
    window.addEventListener('mouseup', () => { isDragging = false; });
    renderer.domElement.addEventListener('wheel', (e) => {
      e.preventDefault();
      distance = Math.max(50, Math.min(500, distance + e.deltaY * 0.2));
    });

    let reqId;
    const animate = () => {
      if (!isDragging) cameraTheta += 0.001; // Auto orbit
      updateCam();
      renderer.render(scene, camera);
      reqId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(reqId);
      renderer.dispose();
      renderer.domElement.removeEventListener('click', onClick);
    };
  }, [tieredConcepts, statusById]);

  // Handle Search
  const handleSearch = (e) => {
    setSearchQuery(e.target.value);
    const match = tieredConcepts.find(c => c.name.toLowerCase().includes(e.target.value.toLowerCase()));
    if (match && e.target.value.length > 2) setSelectedNode(match);
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "500px", borderRadius: "14px", overflow: "hidden", border: "1px solid var(--panel-border)" }}>
      {/* 3D Canvas Container */}
      <div ref={containerRef} style={{ width: "100%", height: "100%", cursor: "grab" }} />

      {/* Floating Search Bar */}
      <div style={{ position: "absolute", top: 16, right: 16, zIndex: 10 }}>
        <input 
          type="text" 
          placeholder="Search concepts..." 
          value={searchQuery}
          onChange={handleSearch}
          style={{ width: "180px", padding: "8px 12px", background: "rgba(14, 11, 8, 0.8)", backdropFilter: "blur(4px)", border: "1px solid var(--panel-border)", borderRadius: "8px", color: "var(--text)", fontSize: "12px" }}
        />
      </div>

      {/* Dynamic Breadcrumb Path */}
      {selectedNode && (
        <div style={{ position: "absolute", top: 16, left: 16, zIndex: 10, display: "flex", gap: "6px", alignItems: "center", background: "rgba(14, 11, 8, 0.8)", backdropFilter: "blur(4px)", padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--panel-border)" }}>
          <span style={{ fontSize: "11px", color: "var(--gold)", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "0.05em", marginRight: "4px" }}>Path:</span>
          {getBreadcrumbPath(selectedNode.id).map((node, i, arr) => (
            <React.Fragment key={node.id}>
              <span style={{ fontSize: "12px", color: i === arr.length - 1 ? "var(--text)" : "var(--text-dim)", fontWeight: i === arr.length - 1 ? "bold" : "normal" }}>
                {node.name}
              </span>
              {i < arr.length - 1 && <span style={{ color: "var(--text-dim)", fontSize: "10px" }}>➔</span>}
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Floating Summary Card */}
      {selectedNode && (
        <div style={{ position: "absolute", bottom: 16, right: 16, zIndex: 10, width: "280px", background: "rgba(14, 11, 8, 0.9)", backdropFilter: "blur(8px)", border: "1px solid var(--panel-border)", borderRadius: "12px", padding: "16px", boxShadow: "0 10px 30px rgba(0,0,0,0.5)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
            <span className={`pill ${statusById[selectedNode.id] || 'unseen'}`}>{statusById[selectedNode.id] || 'unseen'}</span>
            <button onClick={() => setSelectedNode(null)} style={{ background: "transparent", border: "none", color: "var(--text-dim)", cursor: "pointer" }}>✕</button>
          </div>
          <h3 style={{ margin: "0 0 4px 0", fontSize: "18px", fontFamily: "var(--serif)" }}>{selectedNode.name}</h3>
          <p style={{ margin: "0 0 12px 0", fontSize: "11px", color: "var(--gold)", textTransform: "uppercase" }}>{selectedNode.category || "Concept"}</p>
          <p style={{ margin: "0 0 16px 0", fontSize: "12px", color: "var(--text-dim)", lineHeight: 1.4 }}>{selectedNode.desc || "Fundamental AI/ML concept."}</p>
          <button className="primary" style={{ width: "100%" }} onClick={() => onSelect?.(selectedNode.id)}>
            Diagnose this node
          </button>
        </div>
      )}
    </div>
  );
}

// --- Main Progress View ---
export default function Progress({ userId, onDiagnoseConcept }) {
  const [data, setData] = useState(null);
  const [concepts, setConcepts] = useState([]);
  const [recs, setRecs] = useState(null);
  const [recsError, setRecsError] = useState("");
  const [error, setError] = useState("");

  function load() {
    setError("");
    api.getProgress(userId).then(setData).catch((e) => setError(e.message));
    api.listConcepts().then(setConcepts).catch((e) => setError(e.message));
    setRecsError("");
    api.getRecommendations(userId).then(setRecs).catch((e) => setRecsError(e.message));
  }

  useEffect(load, [userId]);

  const touched = data && data.mastered + data.weak > 0;
  const statusById = data ? Object.fromEntries(data.entries.map((e) => [e.concept_id, e.status])) : {};

  return (
    <>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <div className="label">Live Progress Map</div>
        <h2>{userId}'s concept graph</h2>
        {data && !touched && (
          <p className="small">
            No progress yet —{" "}
            <a href="#" onClick={(e) => { e.preventDefault(); onDiagnoseConcept?.(); }} style={{ color: "var(--gold)" }}>
              start your first diagnosis
            </a>.
          </p>
        )}
        <button className="ghost" onClick={load}>Refresh</button>
      </div>

      {data && (
        <div className="stat-row">
          <Stat n={data.mastered} l="Mastered" />
          <Stat n={data.weak} l="Weak" />
          <Stat n={data.unseen} l="Unseen" />
        </div>
      )}

      {/* Embedded 3D Galaxy Engine replaces the flat SVG ConceptMap */}
      {concepts.length > 0 && (
        <div className="card">
          <div className="label">3D Concept Galaxy</div>
          <h2 style={{ fontSize: 18 }}>How everything connects</h2>
          <p className="small" style={{ marginBottom: "16px" }}>
            Drag to orbit, scroll to zoom. Nodes glow brighter as you master them. Click a node to reveal its dependency path and summary.
          </p>
          <ThreeGalaxyMap concepts={concepts} statusById={statusById} onSelect={onDiagnoseConcept} />
        </div>
      )}

      <div className="card">
        <div className="label">What to learn next</div>
        <h2 style={{ fontSize: 18 }}>Recommended topics</h2>
        {recsError && <p className="small">Couldn't load recommendations: {recsError}</p>}
        {!recsError && recs && recs.length === 0 && (
          <p className="small">Nothing queued up — every unlocked concept is mastered.</p>
        )}
        {recs && recs.map((r) => (
          <div key={r.concept_id} style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <strong style={{ fontSize: 13 }}>{r.name}</strong>
              <span className={`pill ${r.status}`}>{r.status}</span>
            </div>
            <p className="small" style={{ margin: "2px 0" }}>{r.reason}</p>
            {r.related.length > 0 && (
              <p className="small">Related: {r.related.map((h) => h.name).join(", ")}</p>
            )}
            <button className="ghost" onClick={() => onDiagnoseConcept?.(r.concept_id)}>
              Diagnose this
            </button>
          </div>
        ))}
      </div>

      {data && (
        <div className="progress-grid">
          {data.entries.map((e) => (
            <div
              className={`progress-tile ${e.status}`}
              key={e.concept_id}
              style={{ cursor: "pointer" }}
              onClick={() => onDiagnoseConcept?.(e.concept_id)}
              title="Diagnose this concept"
            >
              <div className="name">{e.name}</div>
              <span className={`pill ${e.status}`}>{e.status}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function Stat({ n, l }) {
  return (
    <div className="stat">
      <div className="n">{n}</div>
      <div className="l">{l}</div>
    </div>
  );
}