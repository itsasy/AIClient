import { API_BASE } from "./config.js";
import { api } from "./api.js";
import { ensureSession } from "./auth.js";
import { escapeHtml, money } from "./components.js";

const payButton = document.querySelector("#pay");
const status = document.querySelector("#status");
const badge = document.querySelector("#apiBadge");
let method = "efectivo";
let currency = "ARS";
const cart = new Map();
let idempotencyKey = crypto.randomUUID();

function renderCart(products) { const lines=document.querySelector("#lines"); lines.innerHTML=[...cart.entries()].map(([sku,quantity])=>{const product=products.find((item)=>item.sku===sku);return `<tr><td>${escapeHtml(sku)}</td><td>${escapeHtml(product?.nombre)}</td><td><input class="cart-quantity" data-sku="${escapeHtml(sku)}" type="number" min="0" step="1" value="${quantity}"></td><td>${money(product?.precio)}</td><td>${money(Number(product?.precio||0)*quantity)}</td></tr>`;}).join("")||'<tr><td colspan="5">No hay productos seleccionados</td></tr>'; const total=[...cart.entries()].reduce((sum,[sku,quantity])=>{const product=products.find((item)=>item.sku===sku);return sum+Number(product?.precio||0)*quantity;},0); document.querySelector("#total").textContent=money(total); payButton.disabled=cart.size===0; lines.querySelectorAll(".cart-quantity").forEach((input)=>input.addEventListener("change",()=>{const quantity=Number(input.value||0);if(quantity<=0)cart.delete(input.dataset.sku);else cart.set(input.dataset.sku,quantity);renderCart(products);})); }
async function loadProducts() { const data=await api.catalog.list(); const products=data.items||[]; const picker=document.querySelector("#productPicker"); picker.innerHTML=products.map((product)=>`<option value="${escapeHtml(product.sku)}">${escapeHtml(product.nombre)} · ${money(product.precio)}</option>`).join(""); if(products.length){cart.set(products[0].sku,1);renderCart(products);} picker.addEventListener("change",()=>{const sku=picker.value;if(sku)cart.set(sku,(cart.get(sku)||0)+1);renderCart(products);}); }
document.querySelectorAll("[data-method]").forEach((button)=>button.addEventListener("click",()=>{method=button.dataset.method;document.querySelectorAll("[data-method]").forEach((item)=>item.classList.toggle("active",item===button));}));
document.querySelector("#currency").addEventListener("change",(event)=>{currency=event.target.value;});
payButton.addEventListener("click",async()=>{payButton.disabled=true;status.className="";status.textContent="Procesando...";try{const data=await api.sales.create([...cart.entries()],method,currency,idempotencyKey);if(!data.ok)throw new Error(data.error||"Pago rechazado");status.className="ok";status.textContent=`OK ${data.total} · ${(data.payment||{}).payment_id||""} · ${data.estado} · caja ${data.cash_balance}`;idempotencyKey=crypto.randomUUID();cart.clear();renderCart([]);}catch(error){status.className="err";status.textContent=`Error: ${error.message}`;}finally{payButton.disabled=false;}});
payButton.disabled = true;
ensureSession().then((valid) => { if (valid) { payButton.disabled = false; loadProducts().catch((error)=>{status.className="err";status.textContent=error.message;}); } else { status.className="err"; status.textContent="Sesión requerida para cobrar"; } });
api.health().then((data)=>{badge.textContent=data.ok?"API ok · mock":"API offline";}).catch(()=>{badge.textContent="API offline";badge.classList.add("off");});
if(new URLSearchParams(location.search).get("embed")==="1"){document.documentElement.classList.add("embed");document.querySelector("header a").hidden=true;}
export { API_BASE };
