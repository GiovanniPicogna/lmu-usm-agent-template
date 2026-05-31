# Analytical Toolkit — Domain-Specific Formulae
# Used by `@analytical-agent`. Load only the section relevant to the domain.
# All inputs must be `astropy.Quantity` objects (Iron Rule 2).

---

## Disk / planet formation

Load `.github/skills/pluto/SKILL.md` and `.github/skills/fargo3d/SKILL.md`
for simulation code context alongside these formulae.

```python
import numpy as np
import astropy.units as u
import astropy.constants as c

# ── Geometry ──────────────────────────────────────────────────────────────────

def hill_radius(a, m_p, m_star):
    """Hill sphere radius."""
    return a * (m_p / (3 * m_star)) ** (1/3)

# ── Gap opening ───────────────────────────────────────────────────────────────

def crida_parameter(q, h, alpha):
    """Crida et al. 2006 gap-opening criterion.
    q = M_p/M_star (dimensionless), h = H/r (aspect ratio), alpha = viscosity.
    K > 1 → gap opens (nonlinear regime).
    Ref: 2006Icar..181..587C
    """
    rH_over_a = (q / 3) ** (1/3)          # Hill radius / semi-major axis
    return (3/4) * (h / rH_over_a) + 50 * alpha * h**2 / q

# ── Migration ─────────────────────────────────────────────────────────────────

def type_i_migration_time(m_p, m_star, Sigma_p, a, h, p=0.5):
    """Tanaka et al. 2002 Type-I migration timescale.
    p = surface density power-law slope (Σ ∝ r^-p); default 0.5.
    Only valid for q << h³ (linear regime). Check crida_parameter() first.
    Ref: 2002ApJ...565.1257T
    """
    q = (m_p / m_star).decompose()
    Omega = np.sqrt(c.G * m_star / a**3)
    coeff = 2.73 + 1.08 * p           # torque coefficient for slope p
    t_mig = (1 / coeff) * (m_star / m_p) * (m_star / (Sigma_p * a**2)) * h**2 / Omega
    return t_mig.to(u.yr)

# ── Dust ─────────────────────────────────────────────────────────────────────

def stokes_number(a_grain, rho_grain, Sigma_gas):
    """Epstein-regime Stokes number. Valid when a_grain << λ_mfp.
    Ref: 1977MNRAS.180...57W
    """
    return (np.pi / 2) * (a_grain * rho_grain / Sigma_gas).decompose()

def radial_drift_velocity(St, eta, v_K):
    """Radial drift velocity of a dust particle (Nakagawa et al. 1986).
    eta = (1/2)(H/r)² |d ln P / d ln r|  (dimensionless pressure gradient).
    Ref: 1986Icar...67..375N
    """
    return (-2 * St / (1 + St**2) * eta * v_K).to(u.m / u.s)

def a_frag(Sigma_gas, v_frag, alpha, c_s, rho_grain):
    """Birnstiel et al. 2012 fragmentation barrier grain size.
    a_frag = (2 Σ_gas v_frag²) / (π α ρ_grain c_s²)
    Ref: 2012A&A...539A.148B
    """
    return ((2 / np.pi) * (Sigma_gas * v_frag**2) / (alpha * rho_grain * c_s**2)).to(u.cm)

# ── Stability criteria ────────────────────────────────────────────────────────

def toomre_q(c_s, Omega, Sigma):
    """Toomre Q parameter. Q < 1 → gravitational instability.
    Ref: 1964ApJ...139.1217T
    """
    return (c_s * Omega / (np.pi * c.G * Sigma)).decompose()

# Q > 1: stable; Q < 1: Toomre unstable (gravitational fragmentation)
# Rayleigh: d(r²Ω)/dr > 0 (centrifugal stability)
# Streaming instability onset: ε = Σ_d/Σ_g ≳ St^(1/2) η  (Youdin & Goodman 2005)
```

**Example call (disk, SI units via astropy):**
```python
q     = (1e-3 * u.M_jup / u.M_sun).decompose()  # 1 M_Jup / 1 M_sun
h     = 0.05                                     # H/r at planet location
alpha = 1e-3
K = crida_parameter(q.value, h, alpha)
print(f"Crida K = {K:.2f}  →  {'gap opens' if K > 1 else 'no gap'}")
```

---

## Cosmological simulations

```python
import numpy as np
import astropy.units as u
import astropy.constants as c

def t_virial(M_200, r_200, mu=0.59):
    """Virial temperature of a halo.
    mu = mean molecular weight (0.59 for fully ionised solar-abundance plasma).
    Ref: 1998ApJ...495...80B
    """
    return (mu * c.m_p * c.G * M_200 / (2 * c.k_B * r_200)).to(u.keV, equivalencies=u.temperature_energy())

def jeans_mass(T, rho, mu=1.22):
    """Jeans mass for a uniform medium.
    mu = 1.22 for neutral gas; 0.59 for fully ionised.
    Ref: 1902RSPTA.199....1J
    """
    cs = np.sqrt(c.k_B * T / (mu * c.m_p))
    lambda_J = cs * np.sqrt(np.pi / (c.G * rho))
    return (rho * (4/3) * np.pi * (lambda_J / 2)**3).to(u.M_sun)

def t_cool(n_e, kT, Lambda):
    """Cooling time for a fully-ionised hydrogen plasma.
    n_total = n_e + n_i ≈ 2 n_e  →  thermal energy density = 3 n_e k_B T.
    Lambda = cooling function [erg cm³ s⁻¹].
    Ref: 1988ApJ...325...74S
    """
    return (3 * n_e * c.k_B * kT / (n_e**2 * Lambda)).to(u.Gyr)

def c_sound(kT, mu=0.59):
    """Sound speed in fully ionised ICM plasma."""
    return np.sqrt(c.k_B * kT / (mu * c.m_p)).to(u.km / u.s)
```

---

## Atmospheric retrievals (petitRADTRANS)

```python
import numpy as np
import astropy.units as u
import astropy.constants as c

def scale_height(T, g, mu_mean):
    """Atmospheric scale height. g in m/s², mu_mean in atomic mass units."""
    return (c.k_B * T / (mu_mean * c.m_p * g)).to(u.km)

def transit_depth_per_scale_height(R_p, R_star, H):
    """Change in transit depth per atmospheric scale height.
    Returns dimensionless fraction Δ(R_p/R_star)² per H.
    Ref: 2000ApJ...537..916S
    """
    return (2 * R_p * H / R_star**2).decompose()

def t_eq(T_star, R_star, a_orb, albedo=0.1):
    """Planet equilibrium temperature (uniform heat redistribution, f=1/4).
    Ref: 2007ApJ...667L.191F
    """
    return (T_star * np.sqrt(R_star / (2 * a_orb)) * (1 - albedo)**(1/4)).to(u.K)
```

---

## X-ray spectroscopy / galaxy clusters

```python
import numpy as np
import astropy.units as u
import astropy.constants as c

def emission_measure(n_e, V):
    """Volume emission measure EM = ∫ n_e² dV [cm⁻³]."""
    return (n_e**2 * V).to(u.cm**-3)

def hydrostatic_mass(r, kT, d_ln_rho_d_ln_r, d_ln_T_d_ln_r, mu=0.59):
    """Hydrostatic equilibrium cluster mass within radius r.
    Gradients are dimensionless logarithmic derivatives.
    Ref: 1988ApJ...325...74S
    """
    return (-(c.k_B * kT / (mu * c.m_p * c.G)) * r *
            (d_ln_rho_d_ln_r + d_ln_T_d_ln_r)).to(u.M_sun)
```

---

## Large-scale structure / inference

> **Note:** `lss` analytical estimates are available here but the pipeline
> currently has no `@setup-agent` or simulation skill for this domain.
> The `AnalyticalHandoff` is the final pipeline output for `lss` questions;
> present results directly to the user and skip the gate-6 handoff question.

```python
import numpy as np

def fisher_diagonal(dC_dtheta_list, sigma_list):
    """Diagonal Fisher matrix forecast. Returns F_ii for each parameter."""
    return [float(np.sum((dC**2) / sigma**2)) for dC, sigma in
            zip(dC_dtheta_list, sigma_list)]

def growth_rate(Omega_m_z):
    """Linear growth rate approximation f ≈ Ω_m(z)^0.55 (Linder 2005).
    Ref: 2005PhRvD..72d3529L
    """
    return Omega_m_z**0.55
```
