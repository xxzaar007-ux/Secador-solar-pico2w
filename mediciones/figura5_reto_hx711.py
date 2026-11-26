import re, statistics as s, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
def load(p):
    r=[]
    for l in open(p):
        m=re.match(r'^(\d+),(\d+),(\d+)$',l.strip())
        if m: r.append(tuple(map(int,m.groups())))
    return r
c=load('reto_hx711_c.txt')
m=load('reto_hx711_micropython.txt')
K=300.5/0.67
seg=[x[1] for x in m if 54<=x[0]<85]
mp_sd_g=s.stdev(seg)/K
print('mp seg sd counts',s.stdev(seg),'g',mp_sd_g, 'K',K)
fig,ax=plt.subplots(1,2,figsize=(9,3.6))
lab=['MicroPython','C (Pico SDK)']; col=['#d98c3a','#2f6db3']
t=[371.2,15.9]; lo=[371.2-364,15.9-15]; hi=[388-371.2,22-15.9]
b=ax[0].bar(lab,t,color=col,yerr=[lo,hi],capsize=5)
ax[0].set_ylabel('Tiempo por lectura (µs)'); ax[0].set_title('a) Tiempo de transferencia')
for r,v in zip(b,t): ax[0].text(r.get_x()+r.get_width()/2,v+25,f'{v:.1f} µs',ha='center')
ax[0].set_ylim(0,450)
sd=[mp_sd_g,0.67]
b=ax[1].bar(lab,sd,color=col); ax[1].set_ylabel('Desviación estándar (g)'); ax[1].set_title('b) Precisión con el mismo peso')
for r,v in zip(b,sd): ax[1].text(r.get_x()+r.get_width()/2,v+0.03,f'{v:.2f} g',ha='center')
ax[1].set_ylim(0,1.1)
for a in ax: a.spines[['top','right']].set_visible(False)
plt.tight_layout(); plt.savefig('figura5_reto_hx711.png',dpi=200)
