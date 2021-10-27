import jax.numpy as jnp
import jax


def norm01(tensor):
    return (tensor - tensor.min()) / (tensor.max() - tensor.min())


def axis_color(vector):
    angles = jnp.linspace(-jnp.pi, jnp.pi, vector.shape[-1], endpoint=False)
    probs = jax.nn.softmax(jnp.abs(vector))
    xcoord = (probs * jnp.cos(angles)).sum(axis=-1)
    ycoord = (probs * jnp.sin(angles)).sum(axis=-1)
    return (jnp.arctan2(xcoord, ycoord) + jnp.pi) / (2 * jnp.pi)


##HUE HISTOGRAM CLASS
#   - remembers extent (set automatically in first call)
#   - one hist for count
#   - corresponding hist for hue weight
#   - to display, hue = weight / count, intensity = count