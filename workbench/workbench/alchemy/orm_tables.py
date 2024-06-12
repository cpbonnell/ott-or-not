from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Image(Base):
    __tablename__ = "images"
    hexdigest = Column(String, primary_key=True)
    hashwords = Column(String)
    filepath = Column(String)
    tags = relationship("Tag", secondary="image_tags", back_populates="images")


class Tag(Base):
    __tablename__ = "tags"
    tag = Column(String, primary_key=True)
    images = relationship("Image", secondary="image_tags", back_populates="tags")


class ImageTag(Base):
    __tablename__ = "image_tags"
    hexdigest = Column(String, ForeignKey("images.hexdigest"), primary_key=True)
    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)


def create_database(url="sqlite:///images.db"):
    engine = create_engine(url, echo=True)
    Base.metadata.create_all(engine)


# Example of creating an image with tags
if __name__ == "__main__":
    engine = create_engine("sqlite:///images.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Creating a new image with tags
    new_image = Image(
        hexdigest="abcdef123456",
        hashwords="example hashwords",
        filepath="/path/to/image.jpg",
    )
    landscape_tag = Tag(tag="Landscape")
    portrait_tag = Tag(tag="Portrait")

    new_image.tags.append(landscape_tag)
    new_image.tags.append(portrait_tag)

    session.add(new_image)
    session.commit()
