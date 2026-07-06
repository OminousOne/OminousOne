<div align="center">

<img src="./assets/hero.svg" width="100%" alt="A netcode replay viewer: one Pong match shown from three synchronized views — Client A (predicted), the authoritative server, and Client B (predicted) — with packets flowing between panels. Mid-loop a snapshot is dropped, Client A mispredicts and visibly desyncs, then gets rolled back to the server's truth. All of it is a single animated SVG." />

<br/><br/>

<a href="https://www.linkedin.com/in/julien-dewolfe/"><img src="./assets/btn-linkedin.svg" height="36" alt="linkedin" /></a>&nbsp;
<a href="https://uschedule.ca/"><img src="./assets/btn-uschedule.svg" height="36" alt="uschedule.ca" /></a>&nbsp;
<a href="./tools/simulate.py"><img src="./assets/btn-source.svg" height="36" alt="view the machinery" /></a>

</div>

## the short version

I'm **Julien DeWolfe** — a software engineering student at the University of Ottawa. I started making games at nine in Blender's node-based engine, which led to Unity, C#, game jams, and eventually the problem I still can't put down: **multiplayer**. Not the menus — the part where two machines on opposite ends of a bad connection have to agree on reality sixty times a second.

Everything below is some version of that interest: realtime systems, server-authoritative netcode, and infrastructure that keeps working while things fail around it. I like software that feels instant because someone sweated the parts you can't see.

## what's listening

My projects, the way my router sees them.

| port | service | log |
|:--|:--|:--|
| `:4000/graphql` | **Reciped** · *building now* | The main event: a social recipe platform — import a recipe from anywhere, cook from a feed worth scrolling. Built properly: Fastify + GraphQL API, Next.js web, Flutter mobile, on Postgres, Redis, Kafka, Elasticsearch, and Temporal, with a local LLM doing the recipe parsing. Private repo while it's in the oven. |
| `:27015/udp` | **server-authoritative multiplayer** | Custom TCP/UDP netcode in C#: client prediction, server reconciliation, interpolation. The animation up top is a portrait of this project — gameplay feels instant, but clients don't get to lie. |
| `:7777/udp` | **distributed game server lab** | Kubernetes-backed realtime game servers: scaling, failover, and keeping game state sane while pods come and go. Redis and Mongo behind it, CI/CD in front. |
| `:443/tls` | **[uschedule.ca](https://uschedule.ca/)** | Course scheduling for uOttawa students without the tabs-PDFs-spreadsheet ritual. Live and free. |
| `:3000/http` | **delivery management prototype** | Full-stack restaurant delivery management: Next.js, React, TypeScript, JWT auth, order and menu APIs. The project that taught me web apps are just realtime systems with better fonts. |
| `:9/udp` | `discard` | The games I made at nine live here now. Packets are accepted and lovingly ignored. |

## the loadout

```ini
[realtime]   ; the part I'd do for free
c#, unity, tcp/udp sockets, client prediction, server reconciliation, interpolation

[product]    ; reciped + uschedule run on this
typescript, react, next.js, node, graphql, flutter, tailwind

[infra]      ; where the weekends go
docker, kubernetes, postgres, redis, kafka, elasticsearch, temporal, nginx, github actions
```

## wait — how is a README animated?

<details>
<summary><strong>no gifs, no javascript, no embeds — click for the trick</strong></summary>
<br/>

GitHub strips scripts and styles out of READMEs, but it happily renders an SVG inside an `<img>` — and an SVG is allowed to carry its own stylesheet.

- The hero is **one SVG** (`assets/hero.svg`). The whole match — ball physics, paddle AI, exact loop closure so the rally repeats seamlessly — is simulated ahead of time by [`tools/simulate.py`](./tools/simulate.py) and baked into pure CSS keyframes. It's a stylesheet cosplaying as a game server.
- The three panels replay the same match. The dashed *remote* paddles in the client views run **120 ms in the past** via a negative `animation-delay` — the same interpolation-delay trick real netcode uses.
- The story is scripted like a real incident: at `t≈13.3s` a snapshot from server to Client A dies mid-lane (watch the lower packet lane, left gap). Client A extrapolates from stale state, mispredicts the deflection at `t≈14.05s`, drifts away from the server's ball, and at `t≈15.1s` gets snapped back — red flash, six ticks rewound, inputs replayed. The log at the bottom narrates the whole thing.
- The replay clock, rtt sparklines, interp-buffer cells, and the boot flicker on my name are all keyframes too. `seed 0x4A44` is `JD` in ASCII.
- If your OS asks for reduced motion, the whole thing respects it and freezes on a clean still of the serve.

Refresh the page to restart the match.

</details>

---

<div align="center">
<sub>connection closed by remote host — refresh to replay</sub>
</div>
