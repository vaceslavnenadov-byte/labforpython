// Подгружает схемы вагонов выбранного поезда из API, изображения берутся с CDN
async function showTrain(apiUrl, trainId) {
  const response = await fetch(`${apiUrl}/trains/${trainId}`);
  const train = await response.json();
  const root = document.getElementById("wagons");
  root.innerHTML = "";
  for (const wagon of train.wagons) {
    const div = document.createElement("div");
    div.className = "wagon";
    div.innerHTML = `<h3>Вагон №${wagon.number}</h3><img src="${wagon.scheme_url}" alt="${wagon.wagon_type}">`;
    root.appendChild(div);
  }
}
