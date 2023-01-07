from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket
from random import randint


@task(log_prints=True, retries=3)
def fetch(dataset_url: str) -> pd.DataFrame:
    """Read the data from the web into a pandas DataFrame"""
    # create an artificial failure to show retries

    # if randint(0, 1) > 0:
    #     raise Exception

    df = pd.read_csv(dataset_url)
    return df


@task(log_prints=True)
def clean(df=pd.DataFrame) -> pd.DataFrame:
    """Fix dtype issues"""  # learned from Jupyter exploration
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    print(df.head(2))
    print(f"columns: {df.dtypes}")
    print(f"rows {len(df)}")
    return df


@task
def write_local(df: pd.DataFrame, color: str, dataset_file: str) -> Path:
    """Write DataFrame to local parquet file"""
    path = Path(f"{color}/{dataset_file}.parquet")
    df.to_parquet(f"data/{path}", compression="gzip")
    return path


@task()
def write_gcs(path: Path, color: str) -> None:
    """Upload local parquet file to GCS"""
    gcs_bucket = GcsBucket.load("zoom-gcs")
    gcs_bucket.upload_from_path(from_path=f"data/{path}", to_path=path)
    return


@flow()
def etl_web_to_gcs() -> None:
    """The main extract, transform, and load function"""
    color = "yellow"
    year = 2021
    month = 1
    dataset_file = f"{color}_tripdata_{year}-{month:02}"  # add leading 0 if needed
    dataset_url = f"https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{color}/{dataset_file}.csv.gz"

    df = fetch(dataset_url)
    df_clean = clean(df)
    path = write_local(df_clean, color, dataset_file)
    write_gcs(path, color)

    return


if __name__ == "__main__":
    etl_web_to_gcs()
