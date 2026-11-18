/* PERFIL DA SALA 101: identificação, equipamento controlado e regra de desperdício.
   O sistema monitora UM ambiente (Sala 101) e controla UM equipamento: o ar-condicionado.
   Hoje é um arquivo local; no futuro vem do back-end/banco ("Informações da Sala 101", "Sensores e equipamentos").
   Para trocar: implemente api.getRoomProfile() no serviço (campusApi.js) devolvendo este mesmo formato.
   telemetryKey = campo normalizado da telemetria que informa se o equipamento está ligado. */
(function () {
  const CS = window.CampusSmart;
  CS.data.roomProfile = {
    id: 101, name: 'Sala 101',
    equipment: [
      { id: 'ac', name: 'Ar-condicionado', icon: '❄️', telemetryKey: 'acLigado', onText: 'Ligado', offText: 'Desligado', wasteLevel: 'high',
        wasteReason: 'Sala vazia com o ar-condicionado ligado', wasteType: 'Climatização ligada sem ocupação',
        turnOnLabel: 'Ligar ar-condicionado', turnOffLabel: 'Desligar ar-condicionado' }
    ]
  };
})();
