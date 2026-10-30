"""
Motor de combate por turnos.

No toca la base de datos: recibe dos instancias de Monstruo y devuelve el
resultado. Asi se puede probar con tests sin crear registros, y se puede
reutilizar desde una vista, desde el shell o desde un comando.
"""
import random

TURNOS_MAXIMOS = 40
PROB_CRITICO = 0.15
MULTIPLICADOR_VENTAJA = 1.25


def _dano(atacante, defensor, rng):
    base = atacante.ataque_total - defensor.defensa_total // 2
    base = max(1, base + rng.randint(-4, 4))
    critico = rng.random() < PROB_CRITICO
    if critico:
        base = int(base * 1.5)
    ventaja = atacante.es_fuerte_contra(defensor)
    if ventaja:
        base = int(base * MULTIPLICADOR_VENTAJA)
    return max(1, base), critico, ventaja


def pelear(monstruo_a, monstruo_b, semilla=None):
    """
    Resuelve el combate y devuelve un diccionario:
        {"ganador": Monstruo | None, "turnos": int, "bitacora": [str, ...]}

    'semilla' fija el azar: util para los tests y para repetir una pelea.
    """
    rng = random.Random(semilla)
    clave_a = monstruo_a.pk if monstruo_a.pk is not None else "a"
    clave_b = monstruo_b.pk if monstruo_b.pk is not None else "b"
    hp = {clave_a: monstruo_a.hp, clave_b: monstruo_b.hp}

    bitacora = [
        f"{monstruo_a} ({monstruo_a.get_tipo_display()}, {monstruo_a.hp} HP) "
        f"entra a la arena contra "
        f"{monstruo_b} ({monstruo_b.get_tipo_display()}, {monstruo_b.hp} HP)."
    ]

    # El mas rapido ataca primero: gana el de mayor ataque total.
    orden = sorted(
        [monstruo_a, monstruo_b], key=lambda m: m.ataque_total, reverse=True
    )
    turno = 0

    while turno < TURNOS_MAXIMOS and hp[clave_a] > 0 and hp[clave_b] > 0:
        turno += 1
        for atacante in orden:
            defensor = monstruo_b if atacante is monstruo_a else monstruo_a
            clave_def = clave_b if atacante is monstruo_a else clave_a
            if hp[clave_def] <= 0:
                continue
            golpe, critico, ventaja = _dano(atacante, defensor, rng)
            hp[clave_def] = max(0, hp[clave_def] - golpe)
            detalle = []
            if critico:
                detalle.append("CRITICO")
            if ventaja:
                detalle.append("ventaja de tipo")
            extra = " [" + ", ".join(detalle) + "]" if detalle else ""
            bitacora.append(
                f"Turno {turno}: {atacante.nombre} golpea a {defensor.nombre} "
                f"por {golpe}{extra}. {defensor.nombre} queda con "
                f"{hp[clave_def]} HP."
            )
            if hp[clave_def] == 0:
                bitacora.append(f"{defensor.nombre} cae derrotado.")
                break

    if hp[clave_a] > hp[clave_b]:
        ganador = monstruo_a
    elif hp[clave_b] > hp[clave_a]:
        ganador = monstruo_b
    else:
        ganador = None

    bitacora.append(
        f"Gana {ganador.nombre}." if ganador else "La pelea termina en empate."
    )
    return {"ganador": ganador, "turnos": turno, "bitacora": bitacora}
