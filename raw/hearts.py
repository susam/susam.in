#!/usr/bin/env python3
import matplotlib.pyplot as plt
from matplotlib import ticker
import numpy as np

ax = plt.axes(label='axes')
ax.set_aspect('equal')
ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.25))
ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.25))
plt.tick_params(which='both', left=False, bottom=False)
plt.grid(True, which='major', color='k', linewidth='0.2')
plt.grid(True, which='minor', color='k', linewidth='0.1')
plt.xlim(-4.5, 1)
plt.ylim(-3, 3)

t = np.linspace(0, 2 * np.pi, 1000)
x = 2 * (1 - np.cos(t)) * np.cos(t)
y = 2 * (1 - np.cos(t)) * np.sin(t)
plt.plot(x, y)
plt.xlabel(r'$ x \longrightarrow $')
plt.ylabel(r'$ y \longrightarrow $')
plt.savefig('heart-cardoid.png', dpi=200, bbox_inches='tight')
plt.clf()

# More clumsy equation
x = np.linspace(0.000001, 10, 10000)
y = np.log(x) - x**0.03
plt.plot(x, y) # graph
plt.plot(2.80506, 0, 'm.') # solution
plt.xlim(0, 10)
plt.ylim(-2, 2)
plt.xlabel('x')
plt.ylabel('$ \ln x - x^{0.03} $')
plt.axhline(color='k', linewidth='0.8')
plt.savefig('another', dpi=200, bbox_inches='tight')
plt.clf()
