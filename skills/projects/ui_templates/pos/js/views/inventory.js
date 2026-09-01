import { api } from "../api.js";
import { renderAsync, escapeHtml, tableEmpty } from "./common.js";

export function renderInventory(outlet) {
  const loadFunc = () => api.inventory.list();
  
  return renderAsync(outlet, "Cargando inventario...", loadFunc, (data) => {
    const items = Array.isArray(data) ? data : (data.items || []);
    
    let rowsHtml = '';
    for (const item of items) {
      const isLow = item.quantity <= item.min_quantity;
      const colorStyle = isLow ? 'color: red;' : '';
      rowsHtml += <tr>
        <td></td>
        <td style="font-weight:bold; "></td>
        <td></td>
        <td>
            <button class="btn secondary action-btn" data-sku="" data-action="entry" type="button">Entrada</button>
            <button class="btn secondary action-btn" data-sku="" data-action="exit" type="button">Salida</button>
            <button class="btn secondary action-btn" data-sku="" data-action="adjustment" type="button">Ajuste</button>
            <button class="btn secondary action-btn" data-sku="" data-action="kardex" type="button">Kardex</button>
        </td>
      </tr>;
    }
    
    if(items.length === 0) {
      rowsHtml = tableEmpty(4);
    }
    
    outlet.innerHTML = <div class="panel">
      <h1>Control de Inventario</h1>
      <div class="card" style="margin-bottom:20px;">
        <table>
          <thead>
            <tr><th>SKU</th><th>Cantidad</th><th>Mínimo</th><th>Acciones</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="inventory-kardex" class="card" style="display:none; margin-top:20px;"></div>
    </div>;

    outlet.querySelectorAll('.action-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const sku = btn.dataset.sku;
        const action = btn.dataset.action;
        
        if (action === 'kardex') {
          try {
            const kardex = await api.inventory.kardex(sku);
            const kItems = Array.isArray(kardex) ? kardex : (kardex.items || []);
            let kHtml = <h3>Historial de Movimientos ()</h3><ul>;
            for (const k of kItems) {
              kHtml += <li> |  | Delta:  | Ref:  | Aut: </li>;
            }
            kHtml += '</ul>';
            const kardexContainer = outlet.querySelector('#inventory-kardex');
            kardexContainer.innerHTML = kHtml;
            kardexContainer.style.display = 'block';
          } catch(e) {
            alert('Error: ' + e.message);
          }
          return;
        }
        
        const qtyStr = prompt(Ingrese cantidad para :);
        if (!qtyStr) return;
        const qty = parseInt(qtyStr, 10);
        const ref = prompt("Referencia / Motivo:") || '';
        
        let payload = {};
        if (action === 'adjustment') {
          payload = { product_id: sku, quantity_change: qty, reference: ref };
        } else {
          payload = { product_id: sku, quantity: qty, reference: ref };
        }
        
        try {
          await api.inventory.move(action, payload);
          renderInventory(outlet);
        } catch(e) {
          alert('Error: ' + e.message);
        }
      });
    });
  });
}
