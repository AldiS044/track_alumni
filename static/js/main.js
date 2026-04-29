function showToast(message, type='info') {
  let c=document.querySelector('.toast-container');
  if(!c){c=document.createElement('div');c.className='toast-container';document.body.appendChild(c);}
  const icons={
    success:`<svg viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2.5" width="15" height="15"><path d="M20 6L9 17l-5-5"/></svg>`,
    error:  `<svg viewBox="0 0 24 24" fill="none" stroke="#f87171" stroke-width="2" width="15" height="15"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>`,
    info:   `<svg viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" width="15" height="15"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`,
  };
  const t=document.createElement('div');
  t.className=`toast toast-${type}`;
  t.innerHTML=`${icons[type]||icons.info}<span>${message}</span>`;
  c.appendChild(t);
  setTimeout(()=>{t.style.opacity='0';t.style.transform='translateY(6px)';t.style.transition='.3s ease';},2800);
  setTimeout(()=>t.remove(),3200);
}

function deleteAlumni(id,name){
  if(!confirm(`Hapus alumni "${name}"?\n\nTindakan ini tidak dapat dibatalkan.`)) return;
  fetch(`/alumni/delete/${id}`,{method:'POST'})
    .then(r=>r.json())
    .then(d=>{
      if(d.success){
        showToast(`${name} dihapus`,'success');
        const row=document.querySelector(`tr[data-id="${id}"]`);
        if(row){row.style.transition='.3s ease';row.style.opacity='0';row.style.transform='translateX(-8px)';setTimeout(()=>row.remove(),300);}
      }
    });
}

// Chart defaults — DM Sans + teal palette
Chart.defaults.color='#8a9bb0';
Chart.defaults.borderColor='rgba(13,21,32,.05)';
Chart.defaults.font.family="'DM Sans', sans-serif";
Chart.defaults.font.size=12;

document.addEventListener('DOMContentLoaded',()=>{
  document.querySelectorAll('.filter-auto').forEach(el=>el.addEventListener('change',()=>el.closest('form').submit()));
});
