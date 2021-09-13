"""
A logger that logs training activity to Weights and Biases.
"""

from typing import Dict, Any, Tuple, Callable, List, Optional, IO
import sys

from . import util
from .console import console_logger


# error copied from spacy.errors
E880 = ("[E880] The 'wandb' library could not be found - did you install it? "
        "Alternatively, specify the 'ConsoleLogger' in the 'training.logger' "
        "config section, instead of the 'WandbLogger'.")


# entry point: spacy.WandbLogger.v2
def wandb_logger_v2(
    project_name: str,
    remove_config_values: List[str] = [],
    model_log_interval: Optional[int] = None,
    log_dataset_dir: Optional[str] = None,
):
    try:
        import wandb

        # test that these are available
        from wandb import init, log, join  # noqa: F401
    except ImportError:
        raise ImportError(E880)

    console = console_logger(progress_bar=False)

    def setup_logger(
        nlp: "Language", stdout: IO = sys.stdout, stderr: IO = sys.stderr
    ) -> Tuple[Callable[[Dict[str, Any]], None], Callable[[], None]]:
        config = nlp.config.interpolate()
        config_dot = util.dict_to_dot(config)
        for field in remove_config_values:
            del config_dot[field]
        config = util.dot_to_dict(config_dot)
        run = wandb.init(project=project_name, config=config, reinit=True)
        console_log_step, console_finalize = console(nlp, stdout, stderr)

        def log_dir_artifact(
            path: str,
            name: str,
            type: str,
            metadata: Optional[Dict[str, Any]] = {},
            aliases: Optional[List[str]] = [],
        ):
            dataset_artifact = wandb.Artifact(name, type=type, metadata=metadata)
            dataset_artifact.add_dir(path, name=name)
            wandb.log_artifact(dataset_artifact, aliases=aliases)

        if log_dataset_dir:
            log_dir_artifact(path=log_dataset_dir, name="dataset", type="dataset")

        def log_step(info: Optional[Dict[str, Any]]):
            console_log_step(info)
            if info is not None:
                score = info["score"]
                other_scores = info["other_scores"]
                losses = info["losses"]
                wandb.log({"score": score})
                if losses:
                    wandb.log({f"loss_{k}": v for k, v in losses.items()})
                if isinstance(other_scores, dict):
                    wandb.log(other_scores)
                if model_log_interval and info.get("output_path"):
                    if info["step"] % model_log_interval == 0 and info["step"] != 0:
                        log_dir_artifact(
                            path=info["output_path"],
                            name="pipeline_" + run.id,
                            type="checkpoint",
                            metadata=info,
                            aliases=[
                                f"epoch {info['epoch']} step {info['step']}",
                                "latest",
                                "best"
                                if info["score"] == max(info["checkpoints"])[0]
                                else "",
                            ],
                        )

        def finalize() -> None:
            console_finalize()
            wandb.join()

        return log_step, finalize

    return setup_logger


# entry point: spacy.WandbLogger.v1
def wandb_logger_v1(project_name: str, remove_config_values: List[str] = []):
    try:
        import wandb
        from wandb import init, log, join  # test that these are available
    except ImportError:
        raise ImportError(E880)

    console = console_logger(progress_bar=False)

    def setup_logger(
        nlp: "Language", stdout: IO = sys.stdout, stderr: IO = sys.stderr
    ) -> Tuple[Callable[[Dict[str, Any]], None], Callable[[], None]]:
        config = nlp.config.interpolate()
        config_dot = util.dict_to_dot(config)
        for field in remove_config_values:
            del config_dot[field]
        config = util.dot_to_dict(config_dot)
        wandb.init(project=project_name, config=config, reinit=True)
        console_log_step, console_finalize = console(nlp, stdout, stderr)

        def log_step(info: Optional[Dict[str, Any]]):
            console_log_step(info)
            if info is not None:
                score = info["score"]
                other_scores = info["other_scores"]
                losses = info["losses"]
                wandb.log({"score": score})
                if losses:
                    wandb.log({f"loss_{k}": v for k, v in losses.items()})
                if isinstance(other_scores, dict):
                    wandb.log(other_scores)

        def finalize() -> None:
            console_finalize()
            wandb.join()

        return log_step, finalize

    return setup_logger
