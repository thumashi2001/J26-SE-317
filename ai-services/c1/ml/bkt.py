"""Bayesian Knowledge Tracing (BKT), with and without forgetting. Vectorised so fitting takes seconds."""
import numpy as np
from scipy.optimize import minimize


def make_sequences(df):
    """One sequence per (student, topic). Returns padded arrays and the row index of every cell."""
    groups = df.sort_values(["student_id", "topic", "day", "is_query"]).groupby(["student_id", "topic"], sort=False)
    seqs = []
    for _, g in groups:
        seqs.append(g)
    L = max(len(g) for g in seqs)
    n = len(seqs)
    obs = np.full((n, L), -1, dtype=np.int8)
    gap = np.zeros((n, L))
    idx = np.full((n, L), -1, dtype=np.int64)
    for i, g in enumerate(seqs):
        c = g.correct.values
        d = g.day.values
        m = len(g)
        obs[i, :m] = c  # -1 for queries (no observation)
        gp = np.zeros(m)
        last = d[0]
        for j in range(m):
            gp[j] = 0.0 if j == 0 else d[j] - last
            if c[j] >= 0 or j == 0:
                last = d[j]
        gap[i, :m] = gp
        idx[i, :m] = g.index.values
    return obs, gap, idx


def _sig(x):
    return 1 / (1 + np.exp(-x))


def unpack(theta, forget):
    p_init = _sig(theta[0])
    p_learn = _sig(theta[1])
    slip = 0.3 * _sig(theta[2])
    guess = 0.5 * _sig(theta[3])
    if forget:
        tau = np.exp(theta[4])
        p_floor = _sig(theta[5])
    else:
        tau, p_floor = None, None
    return p_init, p_learn, slip, guess, tau, p_floor


def run(theta, obs, gap, forget):
    """Returns predicted P(correct) at every cell and the log-likelihood."""
    p_init, p_learn, slip, guess, tau, p_floor = unpack(theta, forget)
    n, L = obs.shape
    pL = np.full(n, p_init)
    pred = np.zeros((n, L))
    ll = 0.0
    for j in range(L):
        o = obs[:, j]
        if forget and j > 0:
            r = np.exp(-gap[:, j] / tau)
            pL = np.where(gap[:, j] > 0, pL * r + p_floor * (1 - r), pL)
        p = pL * (1 - slip) + (1 - pL) * guess
        pred[:, j] = p
        seen = o >= 0
        pc = np.clip(p, 1e-6, 1 - 1e-6)
        ll += np.sum(np.where(o == 1, np.log(pc), np.where(o == 0, np.log(1 - pc), 0.0)))
        post = np.where(o == 1, pL * (1 - slip) / pc, np.where(o == 0, pL * slip / (1 - pc), pL))
        nxt = post + (1 - post) * p_learn
        pL = np.where(seen, nxt, pL)
    return pred, ll


def fit(obs, gap, forget):
    best = None
    starts = [np.array([-0.5, -1.0, -2.0, -1.5, 2.0, 0.0]), np.array([0.0, -2.0, -1.0, -1.0, 1.0, -1.0])]
    for s0 in starts:
        x0 = s0 if forget else s0[:4]
        res = minimize(lambda th: -run(th, obs, gap, forget)[1], x0, method="Nelder-Mead", options=dict(maxiter=400, xatol=1e-3, fatol=1e-2))
        if best is None or res.fun < best.fun:
            best = res
    return best.x
