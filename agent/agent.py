import torch

import PIL

import numpy as np

from gym import Env, spaces
from torchvision.transforms import transforms


class Agent(Env):

    def __init__(self, _wrapper_evn, vae, reward_callback=None):

        self._wrapper_env = _wrapper_evn
        self.vae = vae
        self.z_dim = vae.z_dim
        self.reward_callback = reward_callback
        self.n_commands = 2
        self.n_command_history = N_COMMAND_HISTORY
        self.reward_callback = reward_callback
        self.observation_space = spaces.Box(low=np.finfo(np.float32).min,
                                            high=np.finfo(np.float32).max,
                                            shape=(self.z_size + (self.n_commands * self.n_command_history), ),
                                            dtype=np.float32)
        self.action_history = [0.] * (self.n_command_history * self.n_commands)
        self.action_space =spaces.Box(low=np.array([MIN_STEERING, -1]),
                                      high=np.array([MAX_STEERING, 1]), dtype=np.float32)

    def _calc_reward(self, action, done, i_e):
        pass

    def _scaled_action(self, action):
        #Convert from [-1, 1] to [0, 1]
        t = (action[1] + 1) / 2
        action[1] = (1 - t) * MIN_THROTTLE + MAX_THROTTLE * t
        return action

    def _smoothing_action(self, action):
        if self.n_command_history > 0:
            prev_steering = self.action_history[-2]
            max_diff = (MAX_STEERING_DIFF - 1e-5) * (MAX_STEERING - MIN_STEERING)
            diff = np.clip(action[0] - prev_steering, -max_diff, max_diff)
            action[0] = prev_steering + diff
        return action

    def _preprocess_action(self, action):
        action = self._scaled_action(action)
        action = self._smoothing_action(action)
        self._record_action(action)
        return action

    def _encode_image(self, image):
        observe = PIL.Image.fromarray(image)
        croped = observe.crop((0, 40, 160, 120))
        tensor = transforms.ToTensor()(croped)
        tensor.to(self.device)
        z, _, _ = self.vae.encode(torch.stack((tensor,tensor),dim=0)[:-1].to(self.device))
        self._show_debugger(np.asarray(croped)[:,:,::-1], z)
        return z.detach().cpu().numpy()[0]

    def _postprocess_observe(self,observe, action):
        self._record_action(action)
        observe = self._encode_image(observe)
        if self.n_command_history > 0:
            o = np.concatenate([observe, np.asarray(self.action_history)], 0)


    def step(self, action):

        action = self._preprocess_action(action)
        observe, reward, done, e_i = self._wrapped_env.step(action)
        observe = self._postprocess_observe(observe)
        observe = self._postprocess_observe(observe)

        #Override Done event.
        done = np.math.fabs(e_i['cte']) > CTE_ERROR

        if self.reward_callback is not None:
            #Override reward.
            reward = self.reward_callback(action, e_i, done)

        if done:
            self._wrapped_env.step(np.array([0.,0.]))

        return observe, reward, done, e_i


    def render(self):
        self._wrapped_env.render()

    def close(self):
        self._wrapped_env.close()

    def seed(self, seed=None):
        return self._wrapped_env.seed(seed)