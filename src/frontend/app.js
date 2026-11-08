const API_BASE_URL = "http://127.0.0.1:8000/api/v1";
let rooms = [
  {
    id: 101,
    name: "Sala 101",
    floor: "1º andar",
    occupied: true,
    alerts: 2,
    lights: true,
    ac: true,
    last: "há 10min",
    devices: [
      ["Iluminação", "Ligada", true],
      ["Ar-condicionado", "Ligado", true],
      ["Projetor", "Desligado", false],
    ],
  },
  {
    id: 102,
    name: "Sala 102",
    floor: "1º andar",
    occupied: false,
    alerts: 1,
    lights: true,
    ac: true,
    last: "há 45min",
    devices: [
      ["Iluminação", "Ligada", true],
      ["Ar-condicionado", "Ligado", true],
      ["Projetor", "Desligado", false],
    ],
  },
  {
    id: 103,
    name: "Sala 103",
    floor: "1º andar",
    occupied: true,
    alerts: 0,
    lights: true,
    ac: true,
    last: "em uso",
    devices: [
      ["Iluminação", "Ligada", true],
      ["Ar-condicionado", "Ligado", true],
    ],
  },
  {
    id: 104,
    name: "Lab. Informática",
    floor: "1º andar",
    occupied: false,
    alerts: 3,
    lights: true,
    ac: false,
    last: "há 2h 15min",
    devices: [
      ["Iluminação", "Ligada", true],
      ["Climatização", "Desligado", false],
      ["Computadores (8)", "Ligados", true],
      ["Projetor", "Desligado", false],
      ["Impressora", "Ligada", true],
      ["Switch de rede", "Ligado", true],
    ],
  },
  {
    id: 105,
    name: "Auditório",
    floor: "Térreo",
    occupied: false,
    alerts: 2,
    lights: false,
    ac: true,
    last: "há 1h 40min",
    devices: [
      ["Iluminação", "Desligada", false],
      ["Ar-condicionado", "Ligado", true],
      ["Palco", "Ligado", true],
    ],
  },
  {
    id: 201,
    name: "Sala 201",
    floor: "2º andar",
    occupied: true,
    alerts: 0,
    lights: true,
    ac: true,
    last: "em uso",
    devices: [
      ["Iluminação", "Ligada", true],
      ["Ar-condicionado", "Ligado", true],
    ],
  },
  {
    id: 202,
    name: "Sala 202",
    floor: "2º andar",
    occupied: false,
    alerts: 0,
    lights: false,
    ac: false,
    last: "há 3h",
    devices: [
      ["Iluminação", "Desligada", false],
      ["Ar-condicionado", "Desligado", false],
    ],
  },
  {
    id: 203,
    name: "Biblioteca",
    floor: "Térreo",
    occupied: true,
    alerts: 1,
    lights: true,
    ac: true,
    last: "em uso",
    devices: [
      ["Iluminação", "Ligada", true],
      ["Ar-condicionado", "Ligado", true],
      ["Computadores", "Ligados", true],
    ],
  },
];
let alerts = [
  {
    room: 102,
    equip: "Ar-condicionado",
    title: "Sala ociosa com AC ligado",
    priority: "Alta",
    level: "high",
    time: "há 45min",
  },
  {
    room: 104,
    equip: "Computadores (8)",
    title: "Equipamentos ligados sem uso",
    priority: "Alta",
    level: "high",
    time: "há 2h 15min",
  },
  {
    room: 105,
    equip: "Ar-condicionado",
    title: "Sala ociosa com AC ligado",
    priority: "Alta",
    level: "high",
    time: "há 1h 40min",
  },
  {
    room: 104,
    equip: "Iluminação",
    title: "Sala ociosa com luz acesa",
    priority: "Média",
    level: "medium",
    time: "há 2h 15min",
  },
  {
    room: 105,
    equip: "Iluminação",
    title: "Iluminação sem evento ativo",
    priority: "Média",
    level: "medium",
    time: "há 3h",
  },
  {
    room: 203,
    equip: "Computadores",
    title: "Consumo acima do padrão",
    priority: "Baixa",
    level: "low",
    time: "há 30min",
  },
  {
    room: 101,
    equip: "Iluminação",
    title: "Consumo elevado",
    priority: "Baixa",
    level: "low",
    time: "há 20min",
  },
];
let selectedRoom = rooms[3],
  pendingAction = null,
  currentFilter = "Todas";
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
function roomCard(r) {
  return `<button class="room-card ${r.occupied ? "occupied" : ""} ${r.alerts ? "has-alert" : ""}" data-room="${r.id}"><span class="dot"></span><span class="room-copy"><b>${r.name}</b><small>${r.floor} &nbsp; 💡 ${r.lights ? "on" : "—"} &nbsp; ❄ ${r.ac ? "on" : "—"}</small></span><span class="room-side">${r.alerts ? `<span class="count">${r.alerts}</span>` : r.occupied ? "Ocupada" : "Ociosa"}</span><span class="chevron">›</span></button>`;
}
async function fetchRooms(filters = {}) {
  const qs = new URLSearchParams(filters).toString();
  const url = `${API_BASE_URL}/rooms${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);

  const data = await res.json();
  return data.map(adaptRoom);
}
function renderRooms() {
  const q = ($("#searchRoom")?.value || "").toLowerCase();
  const filtered = rooms.filter((r) => {
    const match = r.name.toLowerCase().includes(q) || String(r.id).includes(q);
    const filter =
      currentFilter === "Todas" ||
      (currentFilter === "Ocupadas" && r.occupied) ||
      (currentFilter === "Ociosas" && !r.occupied) ||
      (currentFilter === "Alertas" && r.alerts > 0);
    return match && filter;
  });
  $("#allRooms").innerHTML =
    filtered.map(roomCard).join("") ||
    '<p class="muted">Nenhuma sala encontrada.</p>';
  $("#dashboardRooms").innerHTML = rooms
    .filter((r) => r.alerts || r.occupied)
    .slice(0, 6)
    .map(roomCard)
    .join("");
}
function renderAlerts() {
  $("#alertsList").innerHTML = alerts
    .map(
      (a) =>
        `<article class="alert-card ${a.level === "high" ? "high-border" : ""}"><div class="alert-top"><span class="priority ${a.level}">${a.priority.toUpperCase()}</span><span class="alert-time">${a.time}</span></div><h3>${a.title}</h3><p>${rooms.find((r) => r.id === a.room)?.name} · ${a.equip}</p><div class="alert-actions"><button class="btn" data-view="${a.room}">Ver sala</button><button class="btn primary" data-resolve="${a.room}">Resolver</button></div></article>`,
    )
    .join("");
  const counts = {
    high: alerts.filter((a) => a.level === "high").length,
    medium: alerts.filter((a) => a.level === "medium").length,
    low: alerts.filter((a) => a.level === "low").length,
  };
  $("#highCount").textContent = counts.high;
  $("#mediumCount").textContent = counts.medium;
  $("#lowCount").textContent = counts.low;
  $("#alertCount").textContent = alerts.length;
  $("#navAlertCount").textContent = alerts.length;
  $("#alertsSubtitle").textContent =
    `${alerts.length} desperdícios identificados`;
  $("#recentAlerts").innerHTML = alerts
    .slice(0, 4)
    .map(
      (a) =>
        `<div class="recent-item"><div class="recent-row"><span class="dot ${a.level === "medium" ? "medium" : ""}"></span><span class="recent-copy"><b>${rooms.find((r) => r.id === a.room)?.name}</b><small>${a.equip}</small></span><span class="priority ${a.level}">${a.priority.toUpperCase()}</span></div></div>`,
    )
    .join("");
}
function updateStats() {
  $("#occupiedCount").textContent = rooms.filter((r) => r.occupied).length;
  $("#idleCount").textContent = rooms.filter((r) => !r.occupied).length;
}
function showPage(id) {
  $$(".page").forEach((p) => p.classList.toggle("active", p.id === id));
  $$(".nav-item").forEach((n) =>
    n.classList.toggle("active", n.dataset.go === id),
  );
  if (id === "rooms") renderRooms();
  if (id === "alerts") renderAlerts();
}
function openRoom(id) {
  selectedRoom = rooms.find((r) => r.id === Number(id));
  if (!selectedRoom) return;
  $("#detailName").textContent = selectedRoom.name;
  $("#detailMeta").textContent =
    `Sala ${selectedRoom.id} · ${selectedRoom.floor} · Cap. ${selectedRoom.id === 104 ? "32" : "40"} pessoas`;
  $("#occupancyBadge").textContent = selectedRoom.occupied
    ? "Ocupada"
    : "Ociosa";
  $("#lastUse").textContent = `Último uso ${selectedRoom.last}`;
  $("#wasteNotice").style.display =
    !selectedRoom.occupied && selectedRoom.devices.some((d) => d[2])
      ? "flex"
      : "none";
  $("#mainDevices").innerHTML = selectedRoom.devices
    .slice(0, 2)
    .map(
      (d) =>
        `<div class="device-card"><span class="device-icon">${d[0].toLowerCase().includes("luz") || d[0].toLowerCase().includes("ilum") ? "💡" : "❄️"}</span><span class="device-info"><b>${d[0]}</b><small>${d[1]}</small></span><button class="btn ${d[2] ? "" : "primary"}" data-device="${d[0]}">${d[2] ? "Desligar" : "Ligar"}</button></div>`,
    )
    .join("");
  $("#equipmentList").innerHTML = selectedRoom.devices
    .map(
      (d) =>
        `<div class="equipment"><span class="dot" style="background:${d[2] ? "var(--red)" : "#cfd5de"}"></span><span class="device-info"><b>${d[0]}</b><small class="${d[2] && !selectedRoom.occupied ? "warning" : ""}">${d[2] && !selectedRoom.occupied ? "Ligado sem necessidade" : d[1]}</small></span><button class="btn ${d[2] ? "" : "primary"}" data-device="${d[0]}">${d[2] ? "Desligar" : "Ligar"}</button></div>`,
    )
    .join("");
  showPage("detail");
}
function adaptRoom(r) {
  return { ...r, devices: r.devices.map(d => [d.name, d.status, d.on]) };
}
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2400);
}
function requestOff(device) {
  pendingAction = device;
  const item = selectedRoom.devices.find((x) => x[0] === device);
  const willTurnOn = item ? !item[2] : false;
  $("#confirmModal").dataset.turnOn = String(willTurnOn);
  $("#confirmModal").querySelector("h2").textContent = willTurnOn
    ? "Ligar equipamento?"
    : "Desligar equipamento?";
  $("#confirmModal").querySelector(".modal p").textContent = willTurnOn
    ? "O comando será enviado ao dispositivo para ligá-lo."
    : "O comando será enviado ao dispositivo para desligá-lo.";
  $("#confirmAction").textContent = willTurnOn ? "Ligar" : "Desligar";
  $("#confirmAction").classList.toggle("primary", willTurnOn);
  $("#confirmAction").classList.toggle("danger", !willTurnOn);
  $("#confirmModal").classList.add("show");
  $("#confirmModal").setAttribute("aria-hidden", "false");
}
document.addEventListener("click", (e) => {
  const nav = e.target.closest("[data-go]");
  if (nav) {
    showPage(nav.dataset.go);
    return;
  }
  const room = e.target.closest("[data-room]");
  if (room) {
    openRoom(room.dataset.room);
    return;
  }
  const device = e.target.closest("[data-device]");
  if (device) {
    requestOff(device.dataset.device);
    return;
  }
  const view = e.target.closest("[data-view]");
  if (view) {
    openRoom(view.dataset.view);
    return;
  }
  const resolve = e.target.closest("[data-resolve]");
  if (resolve) {
    openRoom(resolve.dataset.resolve);
    toast("Confira os equipamentos e desligue os que não estão em uso.");
    return;
  }
  const filter = e.target.closest("[data-filter]");
  if (filter) {
    currentFilter = filter.dataset.filter;
    $$(".filter").forEach((b) => b.classList.toggle("selected", b === filter));
    renderRooms();
  }
});
$("#searchRoom").addEventListener("input", renderRooms);
$("#backRooms").addEventListener("click", () => showPage("rooms"));
$("#cancelAction").addEventListener("click", () => {
  $("#confirmModal").classList.remove("show");
  pendingAction = null;
});

$("#confirmAction").addEventListener("click", async () => {
  if (!pendingAction) return;

  const d = selectedRoom.devices.find((x) => x[0] === pendingAction);
  const turnOn = $("#confirmModal").dataset.turnOn === "true";
  const button = $("#confirmAction");
  const cancel = $("#cancelAction");
  const description = $("#confirmModal").querySelector(".modal p");

  button.disabled = true;
  cancel.disabled = true;
  button.textContent = "Processando...";
  description.textContent = "Enviando comando ao equipamento...";

  try {
    await new Promise((resolve) => setTimeout(resolve, 1200));

    const simularErro = false;
    if (simularErro) throw new Error("Falha no comando");

    if (d) {
      d[2] = turnOn;
      d[1] = turnOn ? "Ligado" : "Desligado";
    }

    if (!turnOn) {
      const removed = alerts.filter(
        (a) => a.room === selectedRoom.id && a.equip === pendingAction,
      ).length;

      alerts = alerts.filter(
        (a) => !(a.room === selectedRoom.id && a.equip === pendingAction),
      );

      selectedRoom.alerts = Math.max(0, selectedRoom.alerts - removed);
    } else if (
      !selectedRoom.occupied &&
      !alerts.some(
        (a) => a.room === selectedRoom.id && a.equip === pendingAction,
      )
    ) {
      alerts.unshift({
        room: selectedRoom.id,
        equip: pendingAction,
        title: "Equipamento ligado em sala ociosa",
        priority: "Média",
        level: "medium",
        time: "agora",
      });

      selectedRoom.alerts++;
    }

    $("#confirmModal").classList.remove("show");
    $("#confirmModal").setAttribute("aria-hidden", "true");
    pendingAction = null;

    renderAlerts();
    updateStats();
    openRoom(selectedRoom.id);

    toast(
      turnOn
        ? "Equipamento ligado com sucesso!"
        : "Equipamento desligado com sucesso!",
    );
  } catch (error) {
    description.textContent =
      "Não foi possível executar o comando. Tente novamente.";
    toast("Erro ao executar comando!");
  } finally {
    button.disabled = false;
    cancel.disabled = false;
    button.textContent = turnOn ? "Ligar" : "Desligar";
  }
});

$("#clock").textContent = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
})
  .format(new Date())
  .replace(",", " ·");
async function loadRooms() {
  try {
    rooms = await fetchRooms();
    selectedRoom = rooms.find(r => r.id === 104) ?? rooms[0];
  } catch (err) {
    console.error(err);
    toast("Não foi possível carregar as salas.");
  }
  renderRooms();
  updateStats();
}
(async () => {
  await loadRooms();
  renderAlerts(); // alertas ainda locais; depois use GET /api/v1/alerts
})();
// Integração futura: substituir a simulação local por chamadas fetch à API HTTP do Node-RED.
