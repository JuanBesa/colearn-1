import torch.nn as nn
import torch.nn.functional as nn_func
import torch.utils.data
from torchsummary import summary
from torchvision import transforms, datasets

from colearn_examples.training import initial_result, collective_learning_round, set_equal_weights
from colearn_examples.utils.plot import plot_results, plot_votes
from colearn_examples.utils.results import Results
from colearn_examples_pytorch.utils import categorical_accuracy
from colearn_pytorch.new_pytorch_learner import NewPytorchLearner

"""
MNIST training example using PyTorch

Used dataset:
- MNIST is set of 60 000 black and white hand written digits images of size 28x28x1 in 10 classes

What script does:
- Loads MNIST dataset from torchvision.datasets
- Randomly splits dataset between multiple learners
- Does multiple rounds of learning process and displays plot with results
"""

# define some constants
n_learners = 5
batch_size = 64
n_epochs = 20
vote_threshold = 0.5
train_fraction = 0.9
learning_rate = 0.001
height = 28
width = 28
n_classes = 10
vote_batches = 2
score_name = "categorical accuracy"

no_cuda = False
cuda = not no_cuda and torch.cuda.is_available()
device = torch.device("cuda" if cuda else "cpu")
kwargs = {'num_workers': 1, 'pin_memory': True} if cuda else {}

# Load the data and split for each learner.
train_root = '/tmp/mnist'
data = datasets.MNIST(train_root, transform=transforms.ToTensor(), download=True)
n_train = int(train_fraction * len(data))
n_test = len(data) - n_train
train_data, test_data = torch.utils.data.random_split(data, [n_train, n_test])

data_split = [len(train_data) // n_learners] * n_learners
learner_train_data = torch.utils.data.random_split(train_data, data_split)
learner_train_dataloaders = [torch.utils.data.DataLoader(
    ds,
    batch_size=batch_size, shuffle=True, **kwargs) for ds in learner_train_data]

data_split = [len(test_data) // n_learners] * n_learners
learner_test_data = torch.utils.data.random_split(test_data, data_split)
learner_test_dataloaders = [torch.utils.data.DataLoader(
    ds,
    batch_size=batch_size, shuffle=True, **kwargs) for ds in learner_test_data]


# Define the model
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 20, 5, 1)
        self.conv2 = nn.Conv2d(20, 50, 5, 1)
        self.fc1 = nn.Linear(4 * 4 * 50, 500)
        self.fc2 = nn.Linear(500, n_classes)

    def forward(self, x):
        x = nn_func.relu(self.conv1(x.view(-1, 1, height, width)))
        x = nn_func.max_pool2d(x, 2, 2)
        x = nn_func.relu(self.conv2(x))
        x = nn_func.max_pool2d(x, 2, 2)
        x = x.view(-1, 4 * 4 * 50)
        x = nn_func.relu(self.fc1(x))
        x = self.fc2(x)
        return nn_func.log_softmax(x, dim=1)


# Make n instances of NewPytorchLearner with model and torch dataloaders
all_learner_models = []
for i in range(n_learners):
    model = Net()
    opt = torch.optim.Adam(model.parameters(), lr=learning_rate)
    learner = NewPytorchLearner(
        model=model,
        train_loader=learner_train_dataloaders[i],
        test_loader=learner_test_dataloaders[i],
        device=device,
        optimizer=opt,
        criterion=torch.nn.NLLLoss(),
        num_test_batches=vote_batches,
        vote_criterion=categorical_accuracy,
        minimise_criterion=False
    )

    all_learner_models.append(learner)

# Ensure all learners starts with exactly same weights
set_equal_weights(all_learner_models)

summary(all_learner_models[0].model, input_size=(width, height))

# Train the model using Collective Learning
results = Results()
results.data.append(initial_result(all_learner_models))

for epoch in range(n_epochs):
    results.data.append(
        collective_learning_round(all_learner_models,
                                  vote_threshold, epoch)
    )

    plot_results(results, n_learners, score_name=score_name)
    plot_votes(results)

# Plot the final result with votes
plot_results(results, n_learners, score_name=score_name)
plot_votes(results, block=True)