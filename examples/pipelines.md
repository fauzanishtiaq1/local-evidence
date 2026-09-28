# Data pipelines

Stream checkpoint state is committed only after downstream acknowledgement. Recovery resumes from the last durable offset.

Dead-letter records retain the input partition and offset for replay.
