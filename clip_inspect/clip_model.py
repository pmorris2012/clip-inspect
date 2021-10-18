import jax.numpy as jnp
import haiku as hk
import jax
from functools import partial


##TEMPLATE
class _CLIPModule:
    def __init__(self, state_dict, parent_key, name="", rng_key=4):
        ##CALL super(ModuleName, self).__init__(*args, **kwargs)
        self.state_dict = state_dict
        self.param_key = parent_key + name
        self.rng = jax.random.PRNGKey(rng_key)
        self.dtype = jnp.float32
        self.name = name

    @property
    def input_shape(self):
        return (self.state_dict[self.param_key + ".weight"].shape[-1],)

    @property
    def output_shape(self):
        return (self.state_dict[self.param_key + ".weight"].shape[0],)

    ##DO THIS ONE (Haiku model forward pass)
    @property
    def module(self):
        def fn(input):
            return input
        return fn

    #DO THIS ONE
    def steal_from_state_dict(self, params):
        return params

    @property
    def random_params(self):
        init_tensor = jnp.zeros(self.input_shape, dtype=self.dtype)
        init_fn = hk.transform(self.module).init
        params = init_fn(self.rng, init_tensor)
        return params

    @property
    def params(self):
        params = self.random_params
        params = hk.data_structures.to_mutable_dict(params)
        params = self.steal_from_state_dict(params)
        params = hk.data_structures.to_immutable_dict(params)
        return params

    @property
    def apply_fn(self):
        return hk.without_apply_rng(hk.transform(self.module)).apply

    @property
    def forward(self):
        return partial(self.apply_fn, self.params)


class LayerNorm(_CLIPModule):
    def __init__(self, *args, **kwargs):
        super(LayerNorm, self).__init__(*args, **kwargs)

    @property
    def module(self):
        def fn(input):
            ln = hk.LayerNorm(axis=-1, create_scale=True, create_offset=True, name=self.name[1:])
            return ln(input)
        return fn

    def steal_from_state_dict(self, params):
        params['offset'] = jax.ops.index_update(
            params['offset'],
            jax.ops.index[...],
            jnp.array(self.state_dict[self.param_key + ".bias"].numpy(), dtype=self.dtype)
        )

        params['scale'] = jax.ops.index_update(
            params['scale'],
            jax.ops.index[...],
            jnp.array(self.state_dict[self.param_key + ".weight"].numpy(), dtype=self.dtype)
        )
        return params


@jax.jit
def QuickGELU(input):
    return input * jax.nn.sigmoid(1.702 * input)


class MLP(_CLIPModule):
    def __init__(self, *args, **kwargs):
        super(MLP, self).__init__(*args, **kwargs)

        self.ln = LayerNorm(self.state_dict, self.param_key, name=".ln_2")

    @property
    def input_shape(self):
        return (self.state_dict[self.param_key + ".ln_2.weight"].shape[-1],)

    @property
    def module(self):
        def fn(input):
            norm = self.ln.module(input)
            out = hk.nets.MLP(
                [self.input_shape[0] * 4, self.input_shape[0]], 
                activation=QuickGELU
            )(norm)

            return out
        return fn

    def steal_from_state_dict(self, params):
        params['ln_2'] = self.ln.steal_from_state_dict(params['ln_2'])
        
        params['mlp/~/linear_0']['w'] = jax.ops.index_update(
            params['mlp/~/linear_0']['w'],
            jax.ops.index[...],
            jnp.array(self.state_dict[self.param_key + ".mlp.c_fc.weight"].numpy(), dtype=self.dtype).T
        )
        params['mlp/~/linear_0']['b'] = jax.ops.index_update(
            params['mlp/~/linear_0']['b'],
            jax.ops.index[...],
            jnp.array(self.state_dict[self.param_key + ".mlp.c_fc.bias"].numpy(), dtype=self.dtype)
        )
        params['mlp/~/linear_1']['w'] = jax.ops.index_update(
            params['mlp/~/linear_1']['w'],
            jax.ops.index[...],
            jnp.array(self.state_dict[self.param_key + ".mlp.c_proj.weight"].numpy(), dtype=self.dtype).T
        )
        params['mlp/~/linear_1']['b'] = jax.ops.index_update(
            params['mlp/~/linear_1']['b'],
            jax.ops.index[...],
            jnp.array(self.state_dict[self.param_key + ".mlp.c_proj.bias"].numpy(), dtype=self.dtype)
        )
        return params







