import torch
from functools import partial
from mlutils.measures import *
from mlutils.training import early_stopping, MultipleObjectiveTracker, eval_state
from scipy import stats
from tqdm import tqdm
import warnings
from ..utility.nn_helpers import set_random_seed
import numpy as np

def early_stop_trainer(model, seed, stop_function='corr_stop',
                       loss_function='PoissonLoss', epoch=0, interval=1, patience=10, max_iter=50,
                       maximize=True, tolerance=1e-5, device='cuda', restore_best=True,
                       lr_init=0.003, lr_decay_factor=0.5, lr_decay_patience=5, lr_decay_threshold=0.001,
                       min_lr=0.0001, optim_batch_step = True, train_loader=train, val_loader=val, test_loader=test):
    """"
    Args:
        model: PyTorch nn module
        seed: random seed
        trainer_config:
            lr_schedule: list or ndarray that contains lr and lr decrements after early stopping kicks in
            stop_function: stop condition in early stopping, has to be one string of the following:
                'corr_stop'
                'gamma stop'
                'exp_stop'
                'poisson_stop'
            loss_function: has to be a string that gets evaluated with eval()
                Loss functions that are built in at mlutils that can
                be selected in the trainer config are:
                    'PoissonLoss'
                    'GammaLoss'
            device: Device that the model resides on. Expects arguments such as torch.device('')
                Examples: 'cpu', 'cuda:2' (0-indexed gpu)
        train_loader: PyTorch DtaLoader -- training data
        val_loader: validation data loader
        test_loader: test data loader -- not used during training

    Returns:
        loss: training loss after each epoch
            Expected format: ndarray or dict
        output: user specified output of the training procedure.
            Expected format: ndarray or dict
        model_state: the full state_dict() of the trained model
    """

    # --- begin of helper function definitions

    def model_predictions(val_loader, model):
        """
        computes model predictions for a given dataloader and a model
        Returns:
            target: ground truth, i.e. neuronal firing rates of the neurons
            output: responses as predicted by the network
        """
        target, output = np.array([]), np.array([])

        # loop over loaders
        for data_key, loader in val_loader.items():
            for images, responses in loader:
                output = np.append(output,(model(images, data_key).detach().cpu().numpy()))
                target = np.append(target,responses.detach().cpu().numpy())
            target, output = map(np.vstack, (target, output))
        return target, output

    # all early stopping conditions
    def corr_stop(model):
        with eval_state(model):
            target, output = model_predictions(val_loader, model)

        ret = corr(target, output, axis=0)

        if np.any(np.isnan(ret)):
            warnings.warn('{}% NaNs '.format(np.isnan(ret).mean() * 100))
        ret[np.isnan(ret)] = 0

        return ret.mean()

    def gamma_stop(model):
        with eval_state(model):
            target, output = model_predictions(val_loader, model)

        ret = -stats.gamma.logpdf(target + 1e-7, output + 0.5).mean(axis=1) / np.log(2)
        if np.any(np.isnan(ret)):
            warnings.warn(' {}% NaNs '.format(np.isnan(ret).mean() * 100))
        ret[np.isnan(ret)] = 0
        return ret.mean()

    def exp_stop(model, bias=1e-12, target_bias=1e-7):
        with eval_state(model):
            target, output = model_predictions(val_loader, model)
        target = target + target_bias
        output = output + bias
        ret = (target / output + np.log(output)).mean(axis=1) / np.log(2)
        if np.any(np.isnan(ret)):
            warnings.warn(' {}% NaNs '.format(np.isnan(ret).mean() * 100))
        ret[np.isnan(ret)] = 0
        # -- average if requested
        return ret.mean()

    def poisson_stop(model):
        with eval_state(model):
            target, output = model_predictions(val_loader, model)

        ret = (output - target * np.log(output + 1e-12))
        if np.any(np.isnan(ret)):
            warnings.warn(' {}% NaNs '.format(np.isnan(ret).mean() * 100))
        ret[np.isnan(ret)] = 0
        # -- average if requested
        return ret.mean()

    def full_objective(model, data_key, inputs, targets, **kwargs):
        """
        Computes the training loss for the model and prespecified criterion
        Args:
            inputs: i.e. images
            targets: neuronal responses that the model should predict

        Returns: training loss of the model
        """
        return criterion(model(inputs.to(device), data_key, **kwargs), targets.to(device)) \
                + model.regularizer(data_key)

    def run(model, full_objective, optimizer, scheduler, stop_closure, train_loader,
            epoch, interval, patience, max_iter, maximize, tolerance,
            restore_best, tracker, optim_batch_step):

        for epoch, val_obj in early_stopping(model, stop_closure,
                                             interval=interval, patience=patience,
                                             start=epoch, max_iter=max_iter, maximize=maximize,
                                             tolerance=tolerance, restore_best=restore_best,
                                             tracker=tracker):
            optimizer.zero_grad()
            scheduler.step(val_obj)
            optim_step_count = len(train_loader.keys()) if optim_batch_step else 1

            for batch_no, (data_key, data) in tqdm(enumerate(cycle_datasets(train_loader)),
                                                      desc='Epoch {}'.format(epoch)):

                loss = full_objective(model, data_key, **data)
                if (batch_no+1) % optim_step_count == 0:
                    optimizer.step()
                    optimizer.zero_grad()
                loss.backward()
            print('Training loss: {}'.format(loss))

        return model, epoch

    # --- end of helper function definitions

    # set up the model and the loss/early_stopping functions
    set_random_seed(seed)
    model.to(device)
    model.train()
    criterion = eval(loss_function)()
    # get stopping criterion from helper functions based on keyword
    stop_closure = eval(stop_function)


    tracker = MultipleObjectiveTracker(poisson=partial(poisson_stop, model),
                                       gamma=partial(gamma_stop, model),
                                       correlation=partial(corr_stop, model),
                                       exponential=partial(exp_stop, model))

    # reduce on plateau feature from pytorch 1.2
    optimizer = torch.optim.Adam(model.parameters(), lr=lr_init)

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer,
                                                           mode='max',
                                                           factor=lr_decay_factor,
                                                           patience=lr_decay_patience,
                                                           threshold=lr_decay_threshold,
                                                           min_lr=min_lr,
                                                           )

    model, epoch = run(model=model,
                       full_objective=full_objective,
                       optimizer=optimizer,
                       scheduler=scheduler,
                       stop_closure=stop_closure,
                       train_loader=train_loader,
                       epoch=epoch,
                       interval=interval,
                       patience=patience,
                       max_iter=max_iter,
                       maximize=maximize,
                       tolerance=tolerance,
                       restore_best=restore_best,
                       tracker=tracker,
                       optim_batch_step=optim_batch_step)

    model.eval()
    tracker.finalize()

    val_output = tracker.log["correlation"]

    # compute average test correlations as the score
    y, y_hat = model_predictions(test_loader, model)
    AvgCorr = corr(y, y_hat, axis=0)

    return np.mean(AvgCorr), val_output, model.state_dict()

