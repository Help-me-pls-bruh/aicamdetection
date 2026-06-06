# SentinelAI — Booth & Competition Prep Checklist

> Booth format: you decorate the day before, then present **6 min + 6 min Q&A** at
> the booth when judges visit, and the booth runs all day to attract people.
> Print this and tick the boxes.

---

## ⏳ 5–7 DAYS BEFORE — finalise & rehearse
- [ ] **Freeze the code.** Stop adding features ~3 days out. A stable demo beats a
      fancy broken one. (`git pull` so every team laptop is identical.)
- [ ] **Cold-boot test:** from a fresh start, launch backend (`python run.py`) +
      dashboard (`streamlit run dashboard/dashboard.py`) + camera
      (`python test_camera.py`). Time how long it takes; write the exact commands on
      a card.
- [ ] **🎥 Record the BACKUP DEMO VIDEO (most important prep item):** 30–60s screen
      capture of (a) hex map refreshing, (b) a dispatch recommendation, (c) the
      camera detecting a person + knife/bag. If wifi/camera/laptop dies on the day,
      you play this and keep talking.
- [ ] **Test `demo_simulate.py`** as the no-camera fallback (lights up the dashboard).
- [ ] **Rehearse the 6-min script** out loud, timed to **≤ 5:40**. Do it 3×.
- [ ] **Assign roles** (speaker order + who owns which Q&A topic — see WIN_STRATEGY §11).
- [ ] **Drill Q&A:** one person plays tough judge, fires questions from
      WIN_STRATEGY §6. Especially rehearse the **"is the map random?"** and
      **"isn't predictive policing biased?"** answers word-for-word.

## 🖨️ 2–3 DAYS BEFORE — materials
- [ ] **Print the poster** (check size/orientation the venue allows). Top = hook +
      architecture diagram; centre = fusion formula + 18%→79%; one H3 map visual;
      bottom = impact + "real vs simulated" box. (See WIN_STRATEGY §9.)
- [ ] **Print handouts:** the 6-min script + Q&A cheat-sheet (1 page each), one per speaker.
- [ ] **Make a QR code** linking to your GitHub repo (or the backup demo video) —
      stick it on the poster/booth so judges can scan and explore later.
- [ ] **Sort the props** (see ⚠️ knife note below).
- [ ] **Full dress rehearsal** with the poster + laptop + camera as if it's the day.

## 🏗️ 1 DAY BEFORE — decorate the booth
- [ ] **Mount the poster at eye level**, judges read top-down — lead with the diagram.
- [ ] **Position the laptop/monitor facing visitors**, with the **hex map
      auto-refreshing on a loop** — it's a moving, colourful attractor that pulls
      people in without you doing anything.
- [ ] **Set up the camera at the booth** angled at the walkway so it **detects
      passers-by live** (green "person/moving" boxes on a big screen = magnetic).
- [ ] **Test the actual booth power outlet + wifi.** If wifi is weak/blocked, plan to
      use a **phone hotspot**. Bring an **extension cord + power strip**.
- [ ] **Leave the demo in a known-good state** so morning setup is just "power on".
- [ ] Tidy cables; clear a spot for the laptop and props.

## ☀️ COMPETITION MORNING
- [ ] Arrive **early**. Power on, launch backend → dashboard → camera **before**
      judges circulate.
- [ ] Confirm: hex map looping ✓, camera detecting ✓, dispatch works ✓, backup video
      on the desktop ✓.
- [ ] Phones charged (hotspot), laptop on charger.
- [ ] Quick team huddle: roles, opening line, who greets judges.
- [ ] Deep breath. You built a real thing — show it with confidence.

## 🎒 WHAT TO BRING (pack the night before)
- [ ] Laptop (+ a second laptop as backup if possible) + **charger**
- [ ] **Extension cord / power strip**
- [ ] Phone with **hotspot** ready
- [ ] Mouse (easier than trackpad at a booth)
- [ ] Printed: poster, 6-min script ×3, Q&A cheat-sheet ×3, QR code
- [ ] Props: **bag** (real) + **knife = a PRINTED PHOTO or plastic/toy replica** (⚠️ below)
- [ ] Tape/blu-tack, scissors, marker (booth fixes)
- [ ] Water (you'll talk a lot)

## ⚠️ IMPORTANT — the knife prop
**Do NOT bring a real knife** to a public/school competition venue — it can breach
venue rules and alarm people/security. Instead, detect a **photo of a knife on your
phone screen** held up to the camera, or a **plastic/toy knife**. Confirm with the
organisers what's allowed. The detection works the same on a printed image.

## 🧲 BOOTH-AS-ATTRACTOR TACTICS (win the foot traffic)
- The **live camera detecting visitors** is your biggest draw — let people see
  *themselves* boxed as "person/moving". They'll stop, then you pitch.
- Keep the **hex map looping** on screen even when not presenting.
- Have a **15-second hook** ready for casual passers-by (not the full 6 min):
  *"This is an AI that watches CCTV, scores how dangerous each area is live, and
  dispatches the nearest patrol — want to see it spot a weapon?"*
- When a **judge** arrives: switch to the full, timed 6-min script.

## ✅ FINAL "AM I READY?" TEST (do this 2 days before)
Can you, cold, in front of someone:
1. Launch the whole system in under 2 minutes? 
2. Deliver the 6-min script under time without notes?
3. Land the 18%→79% moment smoothly?
4. Answer "is it random?" and "isn't this biased?" without hesitating?
5. Recover if the demo fails (play the backup video calmly)?

If yes to all five — you're ready to win.
