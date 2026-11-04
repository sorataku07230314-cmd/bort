/**
 * @file replay.js
 * @description Version 3.0 ⑯ レースリプレイ Canvasアニメーションモジュール
 * スリット ➔ 1M ➔ バック ➔ 2M ➔ ゴール を滑らかに描画
 */

const ReplayEngine = {
  renderFrame(canvasId, progress = 0, courseEval = {}, simResult = null) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const W = 920;
    const H = 380;
    if (canvas.width !== W * 2 || canvas.height !== H * 2) {
      canvas.width = W * 2;
      canvas.height = H * 2;
    }
    const ctx = canvas.getContext("2d");
    ctx.save();
    ctx.scale(2, 2);

    ctx.fillStyle = "#14b8d4";
    ctx.fillRect(0, 0, W, H);

    // 1マーク & 2マーク ブイ
    const buoys = [
      { x: 220, y: 195, name: "1マーク" },
      { x: 700, y: 195, name: "2マーク" }
    ];
    buoys.forEach(b => {
      ctx.save();
      ctx.translate(b.x, b.y);
      ctx.fillStyle = "#ffffff";
      ctx.beginPath(); ctx.arc(0, 0, 16, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#ef4444";
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, 16, -Math.PI * 0.75, -Math.PI * 0.25); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, 16, Math.PI * 0.25, Math.PI * 0.75); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(0, 0, 16, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = "#0f172a"; ctx.font = "900 12px sans-serif"; ctx.textAlign = "center";
      ctx.fillText(b.name, 0, 30);
      ctx.restore();
    });

    // スリットライン & ゴールライン
    ctx.strokeStyle = "#dc2626"; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(470, 245); ctx.lineTo(470, 360); ctx.stroke();
    ctx.fillStyle = "#dc2626"; ctx.font = "bold 10px sans-serif"; ctx.textAlign = "center";
    ctx.fillText("START (スリット)", 470, 372);

    ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(410, 245); ctx.lineTo(410, 360); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#0f172a"; ctx.fillText("GOAL", 410, 372);

    const topCombo = (simResult?.trifectaList?.[0]?.combo || "1-2-4").split("-").map(Number);
    const finishOrder = [...topCombo];
    for (let b = 1; b <= 6; b++) {
      if (!finishOrder.includes(b)) finishOrder.push(b);
    }

    const p = Math.max(0, Math.min(100, Number(progress) || 0));

    for (let c = 1; c <= 6; c++) {
      const obj = courseEval[c] || { boatId: c, expectedSt: 0.14, attackType: "sashi" };
      const bId = obj.boatId || c;
      const bColor = BOAT_COLORS[bId] || BOAT_COLORS[1];
      const rankIdx = finishOrder.indexOf(bId);
      const st = obj.expectedSt || 0.14;

      let x = 470, y = 300, angle = Math.PI;
      if (p <= 20) {
        // ① スリット
        const t = p / 20;
        const stAdv = (0.15 - st) * 320;
        x = 750 - t * 280 - stAdv;
        y = 262 + (c - 1) * 16;
        angle = Math.PI;
      } else if (p <= 45) {
        // ② 1M旋回
        const t = (p - 20) / 25;
        let turnR = 36 + c * 8;
        if (obj.attackType === "sashi" || obj.attackType === "nibanzashi") turnR = 28 + c * 4;
        else if (obj.attackType === "makuri") turnR = 68;
        else if (obj.attackType === "tenkaimachi") turnR = 34;
        const theta = -Math.PI * 0.5 + t * Math.PI;
        x = 220 - Math.cos(theta) * turnR;
        y = 195 + Math.sin(theta) * turnR;
        angle = Math.PI - (theta + Math.PI * 0.5);
      } else if (p <= 68) {
        // ③ バックストレッチ
        const t = (p - 45) / 23;
        const lead = (5 - rankIdx) * 24;
        x = 220 + t * 470 + lead;
        y = 68 + rankIdx * 14;
        angle = 0;
      } else if (p <= 86) {
        // ④ 2M旋回
        const t = (p - 68) / 18;
        const turnR = 34 + rankIdx * 8;
        const theta = Math.PI * 0.5 + t * Math.PI;
        x = 700 + Math.cos(theta) * turnR;
        y = 195 - Math.sin(theta) * turnR;
        angle = theta + Math.PI * 0.5;
      } else {
        // ⑤ ゴール
        const t = (p - 86) / 14;
        const lead = (5 - rankIdx) * 32;
        x = 700 - t * 290 - lead;
        y = 262 + rankIdx * 16;
        angle = Math.PI;
      }

      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle);
      ctx.fillStyle = "rgba(255,255,255,0.45)";
      ctx.beginPath(); ctx.moveTo(-16, -5); ctx.lineTo(-40, -10); ctx.lineTo(-40, 10); ctx.lineTo(-16, 5); ctx.closePath(); ctx.fill();
      ctx.fillStyle = bColor.body; ctx.strokeStyle = "#0f172a"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(-20, -9); ctx.lineTo(10, -9); ctx.lineTo(22, 0); ctx.lineTo(10, 9); ctx.lineTo(-20, 9); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#ffffff";
      ctx.beginPath(); ctx.arc(-4, 0, 7.5, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.save();
      ctx.translate(-4, 0);
      ctx.rotate(-angle);
      ctx.fillStyle = bColor.numText; ctx.font = "900 11px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(String(bId), 0, 1);
      ctx.restore();
      ctx.restore();
    }

    // 上部ステータスバー
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, W, 28);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 12px sans-serif";
    ctx.textAlign = "left";
    const stageText = p <= 20
      ? "① スリット（スタート踏み込み）"
      : p <= 45
        ? "② 1マーク旋回（先マイ・差し・二番差し・まくり攻防）"
        : p <= 68
          ? "③ バックストレッチ（直線伸び比べ）"
          : p <= 86
            ? "④ 2マーク旋回（道中さばき・逆転攻防）"
            : `⑤ ゴールイン（想定決着: ${topCombo.join("-")}）`;
    ctx.fillText(`🎬 展開リプレイ: ${stageText}`, 12, 18);
    ctx.fillStyle = "#38bdf8";
    ctx.textAlign = "right";
    ctx.fillText(`進行: ${Math.round(p)}%`, W - 12, 18);

    ctx.restore();
  }
};
