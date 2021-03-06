from h2o import H2OFrame
from h2o.estimators.random_forest import H2ORandomForestEstimator
from sklearn.pipeline import Pipeline
from sklearn_pandas import DataFrameMapper
from sklearn2pmml import sklearn2pmml
from sklearn2pmml.decoration import Alias, CategoricalDomain, ContinuousDomain
from sklearn2pmml.pipeline import PMMLPipeline
from sklearn2pmml.preprocessing import CutTransformer, ExpressionTransformer
from sklearn2pmml.preprocessing.h2o import H2OFrameCreator

import h2o
import pandas
import sys

audit_df = pandas.read_csv("csv/Audit.csv")
#print(audit_df.head(5))

audit_X = audit_df[audit_df.columns.difference(["Adjusted"])]
audit_y = audit_df["Adjusted"]

h2o.init()

mapper = DataFrameMapper([
	("Education", CategoricalDomain()),
	("Employment", CategoricalDomain()),
	("Gender", CategoricalDomain()),
	("Marital", CategoricalDomain()),
	("Occupation", CategoricalDomain()),
	("Age", [ContinuousDomain(), CutTransformer(bins = [17, 28, 37, 47, 83], labels = ["q1", "q2", "q3", "q4"])]),
	("Hours", ContinuousDomain()),
	("Income", ContinuousDomain()),
	(["Hours", "Income"], Alias(ExpressionTransformer("X[1] / (X[0] * 52)"), "Hourly_Income"))
])
classifier = H2ORandomForestEstimator(ntrees = 17)

predict_proba_transformer = Pipeline([
	("expression", ExpressionTransformer("X[1]")),
	("cut", Alias(CutTransformer(bins = [0.0, 0.75, 0.90, 1.0], labels = ["no", "maybe", "yes"]), "Decision", prefit = True))
])

pipeline = PMMLPipeline([
	("local_mapper", mapper),
	("uploader", H2OFrameCreator()),
	("remote_classifier", classifier)
], predict_proba_transformer = predict_proba_transformer)
pipeline.fit(audit_X, H2OFrame(audit_y.to_frame(), column_types = ["categorical"]))

pipeline.verify(audit_X.sample(100))

sklearn2pmml(pipeline, "pmml/RandomForestAudit.pmml")

if "--deploy" in sys.argv:
	from openscoring import Openscoring

	os = Openscoring("http://localhost:8080/openscoring")
	os.deployFile("RandomForestAudit", "pmml/RandomForestAudit.pmml")