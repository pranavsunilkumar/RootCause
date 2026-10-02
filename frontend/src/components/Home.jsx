import React from "react";
import { api } from "../api.js";

export default function Home({ onNavigate, userId }) {
  async function tryDemo() {
    // seed a believable state client-side so "Try a Demo" is instant
    const seeds = [
      ["vectors", "mastered"],
      ["dot-product", "mastered"],
      ["probability-basics", "mastered"],
      ["chain-rule", "weak"],
    ];
    for (const [conceptId, status] of seeds) {
      try {
        if (status === "mastered") {
          await api.checkNode({ user_id: userId, target_concept: conceptId, concept_id: conceptId, answer: "demo seed: strong answer covering the key ideas" });
        }
      } catch {
        /* best-effort seed; ignore failures so the demo still proceeds */
      }
    }
    onNavigate("progress");
  }

  return (
    <>
      <div className="card hero">
        <div className="who">For self-taught AI/ML learners &amp; CS students</div>
        <h1>
          Stuck on AI/ML? We find what <em>actually</em> broke.
        </h1>
        <p className="small" style={{ fontSize: 14, color: "var(--text)" }}>
          Not a chatbot that re-explains the topic you asked about — a tutor
          that checks the concepts underneath it first.
        </p>

        <div className="steps">
          <Step n="1" title="You get stuck" desc="on any AI/ML concept" />
          <Step n="2" title="We check upstream" desc="its prerequisites, one by one" />
          <Step n="3" title="You fix the root cause" desc="the real broken concept, not a symptom" />
        </div>

        <div className="row" style={{ marginTop: 18 }}>
          <button className="cta" onClick={() => onNavigate("diagnose")}>
            Start Diagnosis
          </button>
          <button className="cta2" onClick={tryDemo}>
            Try a Demo
          </button>
          <button className="ghost" onClick={() => onNavigate("path")}>
            See How It Works
          </button>
        </div>
      </div>

      <div className="grid-2">
        <ModeCard
          title="🧠 Diagnose"
          desc="Pick a concept you're stuck on. Answer a couple of quick checks on its prerequisites. RootCause finds the exact node that broke."
          cta="Start a diagnosis"
          onClick={() => onNavigate("diagnose")}
        />
        <ModeCard
          title="🐞 Bug Hunt"
          desc="A short code snippet with one deliberate misconception-bug. Find the line, get the explanation."
          cta="Hunt a bug"
          onClick={() => onNavigate("bughunt")}
        />
        <ModeCard
          title="🗣️ Teach-Back"
          desc="Explain a concept in your own words. RootCause grades it against the key ideas and asks a follow-up if something's missing."
          cta="Teach it back"
          onClick={() => onNavigate("teachback")}
        />
        <ModeCard
          title="🧭 Path"
          desc="Auto-sequences the next concept to study — the weakest foundational node, or the next one you're ready for."
          cta="See what's next"
          onClick={() => onNavigate("path")}
        />
        <ModeCard
          title="📊 Progress"
          desc="A live map of every concept you've touched — mastered, weak, or not yet seen."
          cta="View progress"
          onClick={() => onNavigate("progress")}
        />
        <ModeCard
          title="🏆 Leaderboard"
          desc="Points for mastered concepts and passed attempts, plus badges earned automatically from your history."
          cta="See rankings"
          onClick={() => onNavigate("leaderboard")}
        />
      </div>

      <div className="card contact-card">
        <div className="who" style={{ marginBottom: 4 }}>Thanks for stopping by</div>
        <h2 style={{ fontSize: 22, margin: "0 0 8px" }}>
          We hope RootCause helps you find what's <em style={{ color: "var(--gold)", fontStyle: "italic" }}>really</em> broken, faster.
        </h2>
        <p className="small" style={{ marginBottom: 20 }}>
          Questions, feedback, or just want to say hi? Reach out — we'd love to hear from you.
        </p>

        <div className="contact-links">
          <ContactLink
            href="mailto:pranavweb18@gmail.com"
            icon="✉️"
            label="Email"
            value="pranavweb18@gmail.com"
          />
          <ContactLink
            href="https://github.com/pranavsunilkumar/RootCause"
            icon="🐙"
            label="GitHub"
            value="pranavsunilkumar/RootCause"
            external
          />
          <ContactLink
            href="https://www.linkedin.com/in/pranav-muchalum-25a9a8323/"
            icon="in"
            label="LinkedIn"
            value="pranav-muchalum"
            external
          />
        </div>
      </div>
    </>
  );
}

function ContactLink({ href, icon, label, value, external }) {
  return (
    <a
      href={href}
      target={external ? "_blank" : undefined}
      rel={external ? "noreferrer" : undefined}
      className="contact-link"
    >
      <span className="contact-link-icon">{icon}</span>
      <span>
        <span className="contact-link-label">{label}</span>
        <span className="contact-link-value">{value}</span>
      </span>
    </a>
  );
}

function Step({ n, title, desc }) {
  return (
    <div className="step">
      <b>{n}</b>
      <div style={{ marginTop: 6, fontWeight: 600, fontSize: 13 }}>{title}</div>
      <div className="small">{desc}</div>
    </div>
  );
}

function ModeCard({ title, desc, cta, onClick }) {
  return (
    <div className="card">
      <h2 style={{ fontSize: 19 }}>{title}</h2>
      <p className="small" style={{ minHeight: 54 }}>
        {desc}
      </p>
      <button className="primary" onClick={onClick}>
        {cta}
      </button>
    </div>
  );
}
