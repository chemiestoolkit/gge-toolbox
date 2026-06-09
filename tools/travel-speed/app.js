/* Attack Speed & Detection — Maxy's Empire Toolkit
   Clean reimplementation of the travel-time + detection model.
   Reference behaviour: GeneralsCamp travel calculator (credited). */

const STORE_KEY = "etb.travel-speed";

// Horse boost % by stable level and horse type.
const HORSE_BONUS = {
  1: { Horse: 6, Warhorse: 10, Courser: 16 },
  2: { Horse: 10, Warhorse: 16, Courser: 27 },
  3: { Horse: 13, Warhorse: 22, Courser: 35 },
};

const $ = (id) => document.getElementById(id);
const num = (id) => Number($(id).value);

function horseBoostPercent(stableLevel, horseType) {
  if (horseType === "none" || stableLevel === 0) return 0;
  const row = HORSE_BONUS[stableLevel];
  return (row && row[horseType]) || 0;
}

// Beginner speed boost: levels <= 25 move faster, fading to 0 at level 25.
function lowLevelBoost(level) {
  if (level > 25) return 0;
  return Math.max(0, -0.1667 * level + 4.167);
}

function hms(sec) {
  if (!Number.isFinite(sec) || sec < 0) return "00:00:00";
  const s = Math.trunc(sec);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const p = (n) => String(n).padStart(2, "0");
  return `${p(h)}:${p(m)}:${p(ss)}`;
}

// Core travel time in seconds for a given distance.
function travelTime(unitSpeed, distance, horseBoost, percentBonus, totalDistance) {
  if (!Number.isFinite(unitSpeed) || unitSpeed <= 0) return NaN;
  if (!Number.isFinite(distance) || distance <= 0) return NaN;

  const fieldsPerSecond = unitSpeed / 10 / (10 * 60);
  let speed = fieldsPerSecond * (1 + percentBonus / 100);
  let dist = distance;

  let horseScale = 1;
  if (horseBoost > 0) {
    if (dist < 100) {
      horseScale += (horseBoost / 100 / 10) * 60 * (Math.log(totalDistance / 2 + 1) / Math.log(8));
    } else {
      horseScale += (horseBoost / 100 / 10) * (totalDistance - 10);
      dist -= 10;
    }
  }
  speed *= horseScale;
  return Math.floor(dist / speed);
}

function detection(rawTimeNoHorse, adjustedTime, distance) {
  const units = num("units");
  const sightBonus = num("sightBonus") || 0;
  let early = (num("earlyDetection") || 0) * (1 + sightBonus / 100);
  const later = num("laterDetection") || 0;

  if (!(units > 0) || !(distance > 0) || !(rawTimeNoHorse > 0)) {
    $("detectionTime").textContent = "00:00:00";
    $("detectionTimeAfter").textContent = "00:00:00";
    return;
  }

  const sightRadius = Math.max(6, 0.6 * Math.pow(units, 0.4)) * (1 + sightBonus / 100);
  let detectSec = rawTimeNoHorse * (sightRadius / distance);
  const factor = Math.max(0.1, (100 + early - later) / 100);
  detectSec = Math.min(detectSec * factor, adjustedTime);

  $("detectionTime").textContent = hms(detectSec);
  $("detectionTimeAfter").textContent = hms(adjustedTime - detectSec);
}

function render() {
  const distance = num("distance");
  const speed = num("speed");
  const level = parseInt($("playerLevel").value, 10) || 1;

  const bonus =
    (num("commander") || 0) + (num("glory") || 0) + (num("vip") || 0) +
    (num("global") || 0) + (num("hol") || 0) + (num("war") || 0);

  const stableLevel = parseInt($("stableLevel").value, 10) || 0;
  const horse = horseBoostPercent(stableLevel, $("horseType").value);

  const rawNoHorse = travelTime(speed, distance, 0, bonus, distance);
  const rawHorse = travelTime(speed, distance, horse, bonus, distance);
  const adjusted = rawHorse / (1 + lowLevelBoost(level));

  $("arrivalTime").textContent = hms(adjusted);
  detection(rawNoHorse, adjusted, distance);

  syncHorseState();
  save();
}

function syncHorseState() {
  const stableLevel = parseInt($("stableLevel").value, 10) || 0;
  const horse = $("horseType");
  if (stableLevel === 0) {
    horse.value = "none";
    horse.disabled = true;
  } else {
    horse.disabled = false;
  }
}

function save() {
  const data = {};
  document.querySelectorAll("input, select").forEach((el) => (data[el.id] = el.value));
  localStorage.setItem(STORE_KEY, JSON.stringify(data));
}

function load() {
  const raw = localStorage.getItem(STORE_KEY);
  if (!raw) return;
  try {
    const data = JSON.parse(raw);
    for (const [id, value] of Object.entries(data)) {
      const el = $(id);
      if (el) el.value = value;
    }
  } catch (_) {}
}

document.querySelectorAll("input, select").forEach((el) => el.addEventListener("input", render));
load();
render();
