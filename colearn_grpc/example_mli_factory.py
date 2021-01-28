import json
from typing import Set, Dict, Any

from colearn.ml_interface import MachineLearningInterface
from colearn_other.mli_factory import TaskType, mli_factory
from colearn_grpc.mli_factory_interface import MliFactory


# TODO Add Documentation
# TODO Add tests
class ExampleMliFactory(MliFactory):

    def __init__(self):
        self.models = {task.name: {} for task in TaskType}
        self.dataloaders = {task.name: {} for task in TaskType}
        self.compatibilities = {task.name: {task.name} for task in TaskType}

    def get_models(self) -> Dict[str, Dict[str, Any]]:
        return self.models

    def get_dataloaders(self) -> Dict[str, Dict[str, Any]]:
        return self.dataloaders

    def get_compatibilities(self) -> Dict[str, Set[str]]:
        return self.compatibilities

    def get_mli(self, model_name: str, model_params: str, dataloader_name: str,
                dataset_params: str) -> MachineLearningInterface:
        if model_name not in self.models:
            raise Exception(f"Model {model_name} is not a valid model. "
                            f"Available models are: {self.models}")
        if dataloader_name not in self.dataloaders:
            raise Exception(f"Dataloader {dataloader_name} is not a valid dataloader. "
                            f"Available dataloaders are: {self.dataloaders}")
        if dataloader_name not in self.compatibilities[model_name]:
            raise Exception(f"Dataloader {dataloader_name} is not compatible with {model_name}."
                            f"Compatible dataloaders are: {self.compatibilities[model_name]}")

        data_config = self.dataloaders[dataloader_name]  # Default parameters
        data_config.update(json.loads(dataset_params))

        train_folder = data_config["train_folder"]
        test_folder = data_config["test_folder"]

        model_config = self.models[model_name]  # Default parameters
        model_config.update(json.loads(model_params))
        model_type = model_config["model_type"]
        model_config.pop('model_type', None)  # Required because model_type is passed as argument as well

        # Join both configs into one big config
        data_config.update(model_config)

        return mli_factory(str_task_type=model_name,
                           train_folder=train_folder,
                           str_model_type=model_type,
                           test_folder=test_folder,
                           **model_config)
